"""Demand screening for additive JAX/DAY service; never publishes a schedule."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from caa_scheduler.bank_placement import TIMEZONE_OFFSETS, _block_minutes
from caa_scheduler.demand import load_demand_sources_from_manifest, parse_airport_od_matrix
from caa_scheduler.io import read_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.planning import haversine_nm


def baseline():
    result = read_json(ROOT / "data/schedules/schedule_7_v1_1_6/canonical_schedule.json")
    for round_number in (1, 2):
        result = apply_optimization_overlay(result, read_json(
            ROOT / f"config/optimizations/schedule_7_v1_2_0_round_{round_number}.json"))
    return result


class DemandScreen:
    """The workbook's relative-choice model, not a passenger-load forecast."""
    def __init__(self, schedule):
        self.schedule = schedule
        self.cities = {c["code"]: c for c in schedule["cities"]}
        self.hubs = set(schedule["operatingPolicy"]["hubs"] + schedule["operatingPolicy"]["focusCities"])
        loaded = load_demand_sources_from_manifest(ROOT / "config/demand_data/bts_db1c_6mo_v7.json", ROOT)
        self.od = parse_airport_od_matrix(loaded["airportOdMatrixText"])["values"]
        self.demand_id = loaded["manifest"]["id"]
        self.distances = {(a, b): haversine_nm(self.cities[a]["latitude"], self.cities[a]["longitude"],
                                             self.cities[b]["latitude"], self.cities[b]["longitude"])
                          for a in self.cities for b in self.cities}
        self.profile = next(p for p in read_json(ROOT / "config/policies/planning_rules_v7.json")
                            ["frequencyAllocation"]["fleetProfiles"] if p["fleet"] == "MAX9")
        self.options = self.enumerate(schedule["legs"])
        self.loads, self.connections = self.allocate(self.options)

    def utc(self, leg):
        departure = (leg["departureMinute"] - TIMEZONE_OFFSETS[self.cities[leg["origin"]]["timezone"]]) % 1440
        arrival = (leg["arrivalMinute"] - TIMEZONE_OFFSETS[self.cities[leg["destination"]]["timezone"]]) % 1440
        return departure, arrival, (arrival - departure) % 1440

    def enumerate(self, legs):
        options = defaultdict(list)
        origins, arrivals = defaultdict(list), defaultdict(list)
        for leg in legs:
            origins[leg["origin"]].append(leg)
            arrivals[leg["destination"]].append(leg)
            block = self.utc(leg)[2]
            options[leg["origin"], leg["destination"]].append({"legs": (leg["id"],),
                "weight": 1 / block ** 2, "elapsed": block, "wait": 0, "hub": "", "circuity": 1})
        minimum = self.schedule["schedule"]["connectionWindowMinutes"]["minimum"]
        maximum = self.schedule["schedule"]["connectionWindowMinutes"]["maximum"]
        for hub in self.hubs:
            for first in arrivals[hub]:
                for second in origins[hub]:
                    a, b = first["origin"], second["destination"]
                    if a == b:
                        continue
                    wait = (self.utc(second)[0] - self.utc(first)[1]) % 1440
                    if not minimum <= wait <= maximum:
                        continue
                    circuity = (self.distances[a, hub] + self.distances[hub, b]) / self.distances[a, b]
                    if circuity > 2.25:
                        continue
                    elapsed = self.utc(first)[2] + wait + self.utc(second)[2]
                    options[a, b].append({"legs": (first["id"], second["id"]),
                        "weight": 0.35 / elapsed ** 2 / circuity ** 2,
                        "elapsed": elapsed, "wait": wait, "hub": hub, "circuity": circuity})
        return options

    def allocate(self, options):
        loads, connections = defaultdict(Counter), defaultdict(list)
        for (a, b), choices in options.items():
            denominator = sum(c["weight"] for c in choices)
            allocated = 0
            for choice in choices:
                opportunity = self.od[a][b] * choice["weight"] / denominator
                allocated += opportunity
                for index, identifier in enumerate(choice["legs"]):
                    side = "local" if len(choice["legs"]) == 1 else ("outbound" if index == 0 else "inbound")
                    loads[identifier][side] += opportunity
                    if side != "local":
                        connections[identifier].append({"origin": a, "destination": b,
                            "opportunity": opportunity, "wait": choice["wait"], "hub": choice["hub"]})
            assert abs(allocated - self.od[a][b]) < 1e-7
        return loads, connections

    def rank_markets(self, hub):
        result = []
        legs = self.schedule["legs"]
        outbound = defaultdict(list)
        for leg in legs:
            if leg["origin"] == hub:
                outbound[leg["destination"]].append(leg)
        for city, outgoing in outbound.items():
            if not 1 <= len(outgoing) <= 3:
                continue
            incoming = [l for l in legs if l["origin"] == city and l["destination"] == hub]
            conn_out = sum(self.loads[l["id"]]["inbound"] for l in outgoing)
            conn_in = sum(self.loads[l["id"]]["outbound"] for l in incoming)
            unique = {(r["origin"], r["destination"]) for l in outgoing + incoming for r in self.connections[l["id"]]}
            top_od = Counter()
            for leg in outgoing + incoming:
                for record in self.connections[leg["id"]]:
                    top_od[record["origin"], record["destination"]] += record["opportunity"]
            result.append({"hub": hub, "city": city, "departuresFromHub": len(outgoing),
                "cityName": self.cities[city]["displayName"],
                "departuresToHub": len(incoming),
                "localOdBothDirections": round(self.od[hub][city] + self.od[city][hub], 3),
                "allocatedConnectingBothDirections": round(conn_out + conn_in, 3),
                "connectingPerDeparture": round((conn_out + conn_in) / (len(outgoing) + len(incoming)), 3),
                "connectingMarkets": len(unique),
                "topConnectingOd": [{"origin": a, "destination": b, "opportunity": round(value, 3)}
                                    for (a, b), value in top_od.most_common(5)],
                "currentFleets": sorted({l["fleet"] for l in outgoing + incoming}),
                "departureTimes": sorted(l["departure"] for l in outgoing),
                "returnTimes": sorted(l["departure"] for l in incoming),
                "max9BlockMinutes": _block_minutes(hub, city, self.profile, self.cities)})
        return sorted(result, key=lambda r: -r["connectingPerDeparture"])


def proposal(schedule, screen, name, pairs, insertion_day):
    """Insert one aircraft-day at a matching overnight boundary, without swaps."""
    route = 700 + insertion_day
    legs, assignments = [], []
    for a, b, departure in pairs:
        block = _block_minutes(a, b, screen.profile, screen.cities)
        arrival = (departure - TIMEZONE_OFFSETS[screen.cities[a]["timezone"]] + block
                   + TIMEZONE_OFFSETS[screen.cities[b]["timezone"]]) % 1440
        leg = {"id": f"V120-GROWTH-{a}-{b}", "origin": a, "destination": b,
               "departureMinute": departure, "arrivalMinute": arrival}
        legs.append(leg)
        for operation, hub, minute in (("departure", a, departure), ("arrival", b, arrival)):
            if hub not in screen.hubs or hub == "BHM":
                continue
            bank = next(bank for bank in schedule["hubBanks"] if bank["hub"] == hub
                        and bank["startMinute"] <= minute < bank["endMinute"])
            assignments.append({"legId": leg["id"], "operation": operation, "bankId": bank["id"]})
    reassignments = [{"sourceRoute": l["route"], "expectedLine": l["line"],
                      "expectedDay": l["day"], "expectedFleet": "MAX9",
                      "targetRoute": l["route"] + 1, "line": l["line"],
                      "day": l["day"] + (l["line"] == "A")}
                     for l in schedule["legs"] if l["fleet"] == "MAX9"
                     and l["sequenceWithinRoute"] == 1 and l["route"] >= route]
    return {"schemaVersion": "1.0.0", "id": f"schedule-7-v1.2.0-{name}-proposal",
            "baseSchedule": {"scheduleId": schedule["schedule"]["id"],
                             "overlays": [f"config/optimizations/schedule_7_v1_2_0_round_{n}.json" for n in (1, 2)]},
            "schedule": {"id": f"schedule_7_v1_2_0_{name}_proposal",
                         "version": f"1.2.0-{name}-proposal", "label": f"Schedule 7 v1.2 {name} proposal",
                         "status": "draft"},
            "initiative": {"kind": "one_spare_max9_additive_growth",
                           "authorizedScope": "One additional active MAX9 from existing inventory, preserving every existing flight and time.",
                           "reviewStatus": "Unpublished proposal; alternatives are mutually exclusive.",
                           "principles": ["No fleet or flight swaps, policy overrides, bank changes, or inventory increases.",
                                          "Insert one aircraft-day at an existing Line A overnight boundary; normalize route/day labels only."]},
            "routeReassignments": reassignments,
            "addRoutes": [{"route": route, "line": "A", "day": insertion_day, "fleet": "MAX9", "legs": legs}],
            "bankAssignmentsToAdd": assignments}


def compare_proposal(schedule, screen, overlay):
    from caa_scheduler.gate_export import export_gate_schedule
    from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
    from caa_scheduler.validation import validate_schedule
    candidate = apply_optimization_overlay(schedule, overlay)
    operating = validate_operating_rules(candidate)
    overnight = validate_overnight_turns(candidate)
    assert validate_schedule(candidate)["status"] == overnight["status"] == "pass"
    assert operating["summary"]["effectiveErrorFindings"] == 0
    assert not any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"])
    old = {l["id"]: l for l in schedule["legs"]}
    excluded = {"route", "day"}
    for l in candidate["legs"]:
        if l["id"] in old:
            assert {k: v for k, v in l.items() if k not in excluded} == {k: v for k, v in old[l["id"]].items() if k not in excluded}
    for key in ("cities", "operatingPolicy", "hubBanks"):
        assert candidate[key] == schedule[key]
    assert candidate["schedule"]["fleetCounts"] == schedule["schedule"]["fleetCounts"]
    options = screen.enumerate(candidate["legs"])
    loads, connections = screen.allocate(options)
    new = [l for l in candidate["legs"] if l["id"] not in old]
    identifiers = {l["id"] for l in new}
    improved, saved_minutes, previously_unserved, unique_opportunity = 0, 0, 0, 0
    for (a, b), choices in options.items():
        demand = screen.od[a][b]
        prior = screen.options.get((a, b), [])
        if not prior:
            previously_unserved += demand
        elif min(c["elapsed"] for c in choices) < min(c["elapsed"] for c in prior):
            improved += 1
            saved_minutes += demand * (min(c["elapsed"] for c in prior) - min(c["elapsed"] for c in choices))
        denominator = sum(c["weight"] for c in choices)
        unique_opportunity += demand * sum(c["weight"] for c in choices if identifiers.intersection(c["legs"])) / denominator
    gates = export_gate_schedule(candidate)
    stands = [s for city in gates["cities"] for s in city["claims"] if s["rowType"] == "stand"]
    rows = []
    for index, l in enumerate(new):
        details = connections[l["id"]]
        row = dict(l)
        row.update({"originName": screen.cities[l["origin"]]["displayName"],
                    "destinationName": screen.cities[l["destination"]]["displayName"],
                    "blockMinutes": screen.utc(l)[2],
                    "localOpportunity": round(loads[l["id"]]["local"], 3),
                    "inboundOpportunity": round(loads[l["id"]]["inbound"], 3),
                    "outboundOpportunity": round(loads[l["id"]]["outbound"], 3),
                    "totalOpportunity": round(sum(loads[l["id"]].values()), 3),
                    "groundMinutesBefore": ((screen.utc(l)[0] - screen.utc(new[index - 1])[1]) % 1440) if index else None,
                    "departureBank": next((a["bankId"] for a in overlay["bankAssignmentsToAdd"]
                                           if a["legId"] == l["id"] and a["operation"] == "departure"), ""),
                    "arrivalBank": next((a["bankId"] for a in overlay["bankAssignmentsToAdd"]
                                         if a["legId"] == l["id"] and a["operation"] == "arrival"), ""),
                    "connectionOptions": len(details),
                    "connectingOdMarkets": len({(d["origin"], d["destination"]) for d in details}),
                    "weightedConnectionWait": round(sum(d["opportunity"] * d["wait"] for d in details) /
                                                     sum(d["opportunity"] for d in details), 1) if details else None})
        rows.append(row)
    return {"name": overlay["id"], "scheduleId": candidate["schedule"]["id"], "legs": rows,
            "summary": {"newLegs": len(new), "newRoundTrips": len(new) // 2,
                        "blockMinutes": sum(screen.utc(l)[2] for l in new),
                        "minimumLegOpportunity": min(r["totalOpportunity"] for r in rows),
                        "uniqueAllocatedItineraryOpportunity": round(unique_opportunity, 3),
                        "odMarketsWithFasterBestItinerary": improved,
                        "demandWeightedBestItineraryMinutesSaved": round(saved_minutes, 3),
                        "previouslyUnservedDirectionalOdDemand": round(previously_unserved, 3),
                        "effectiveOperatingErrors": operating["summary"]["effectiveErrorFindings"],
                        "hardStopFailures": 0, "overnightTurnFailures": len(overnight["findings"]),
                        "operatingWarnings": operating["summary"]["effectiveWarningFindings"],
                        "standClaims": len(stands), "standMinutes": sum(s["end"] - s["start"] for s in stands)},
            "gateConsequences": [{"city": c["code"], "gates": c["nGates"], "stands": c["nStands"],
                                  "standClaims": [p for p in c["claims"] if p["rowType"] == "stand"]}
                                 for c in gates["cities"] if c["code"] in {l["origin"] for l in new}],
            "connections": [{"flight": l["flight"], "legId": l["id"], **d}
                            for l in new for d in connections[l["id"]]]}


def main():
    schedule = baseline()
    screen = DemandScreen(schedule)
    report = {"sourceScheduleId": schedule["schedule"]["id"], "demandId": screen.demand_id,
        "interpretation": "Demand opportunity at full CAA capture before seat constraints; not actual loads or incremental passengers.",
        "JAX": screen.rank_markets("JAX"), "DAY": screen.rank_markets("DAY")}
    core = [("FLL", "JAX", 385), ("JAX", "SFB", 500), ("SFB", "JAX", 593),
            ("JAX", "PIE", 895), ("PIE", "JAX", 995), ("JAX", "FLL", 1115)]
    extended = core[:3] + [("JAX", "PGD", 685), ("PGD", "JAX", 793)] + core[3:]
    joint = [("SFB", "JAX", 370), ("JAX", "DAY", 458), ("DAY", "RFD", 730),
             ("RFD", "DAY", 797), ("DAY", "JAX", 978), ("JAX", "SFB", 1127)]
    report["proposals"] = []
    for name, pairs, day in (("jax_core", core, 2), ("jax_pgd", extended, 2), ("jax_day_rfd", joint, 3)):
        overlay = proposal(schedule, screen, name, pairs, day)
        filename = f"config/proposals/schedule_7_v1_2_0_{name}.json"
        path = ROOT / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(overlay, indent=2) + "\n")
        result = compare_proposal(schedule, screen, overlay)
        result["overlay"] = filename
        report["proposals"].append(result)
        print(name, json.dumps(result["summary"]))
    eligible = {(hub, r["city"]) for hub in ("JAX", "DAY") for r in report[hub]}
    report["currentFlights"] = []
    for l in schedule["legs"]:
        if not ((l["origin"], l["destination"]) in eligible or (l["destination"], l["origin"]) in eligible):
            continue
        record = dict(l)
        record.update({"originName": screen.cities[l["origin"]]["displayName"],
                       "destinationName": screen.cities[l["destination"]]["displayName"],
                       "localOpportunity": round(screen.loads[l["id"]]["local"], 3),
                       "inboundOpportunity": round(screen.loads[l["id"]]["inbound"], 3),
                       "outboundOpportunity": round(screen.loads[l["id"]]["outbound"], 3),
                       "blockMinutes": screen.utc(l)[2]})
        report["currentFlights"].append(record)
    output = ROOT / "builds/schedule_7_v1_2_hub_growth_market_screen.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    for hub in ("JAX", "DAY"):
        print(hub)
        for row in report[hub][:15]:
            print(json.dumps(row))


if __name__ == "__main__":
    main()
