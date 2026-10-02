"""Materialize and analyze the unpublished first v1.2.1 optimization round."""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_schedule_7_v1_2_1_holds import HoldSearch, HOLDS, BASE
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.io import write_json, sha256_file
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.timetable import export_timetable
from caa_scheduler.validation import validate_schedule

OVERLAY = "config/optimizations/schedule_7_v1_2_1_round_1.json"
FLYING = {701: ("PGD", 560, 760), 123: ("BDL", 520, 630),
          321: ("RFD", 1010, 1124), 129: ("DAY", 890, 1095)}
COMPARISONS = {701: ("RDU", 695, 834), 123: ("BWI", 630, 740),
               321: ("BDL", 1006, 1240), 129: ("BLV", 930, 1035)}


def build():
    search = HoldSearch()
    selections = {}
    for route, (city, departure, back) in FLYING.items():
        route_legs = sorted((l for l in search.base["legs"] if l["route"] == route), key=lambda l: l["sequenceWithinRoute"])
        before = route_legs[HOLDS[route][0] - 1]
        hub, fleet = before["destination"], before["fleet"]
        selections[route] = {"legs": [search.leg(hub, city, departure, fleet), search.leg(city, hub, back, fleet)]}
    final = next(l for l in search.base["legs"] if l["id"] == "V115-R321-SYR-PIT")
    retiming = {"legId": final["id"], "expectedDepartureMinute": final["departureMinute"],
                "expectedArrivalMinute": final["arrivalMinute"], "departureMinute": final["departureMinute"] + 11,
                "arrivalMinute": final["arrivalMinute"] + 11,
                "reason": "Allow the new RFD return to arrive eight minutes into SYR Bank 7 and retain 47 minutes before PIT departure."}
    overlay = search.overlay(selections, [retiming])
    overlay["initiative"]["selectionRationale"] = [
        "PHF-PGD and SYR-BDL receive second service with useful opportunity in both directions.",
        "SYR-RFD receives third service; its return opportunity is materially stronger than the late BDL alternative.",
        "MCI-DAY receives second inter-hub service and 80 more block minutes than a third BLV flight; BLV is commercially stronger (593.3 versus DAY's 495.0 combined opportunity in one-at-a-time joint comparisons).",
        "Use modest margins on new flights; shift only the existing late SYR-PIT flight by eleven minutes."]
    write_json(ROOT / OVERLAY, overlay)
    candidate = apply_optimization_overlay(search.base, overlay)
    structural = validate_schedule(candidate)
    operating = validate_operating_rules(candidate)
    overnight = validate_overnight_turns(candidate)
    planning = reconstruct_planning_snapshot(candidate, demand_data_version=search.screen.demand_id)
    planning_validation = validate_planning_snapshot(planning, candidate)
    gates = export_gate_schedule(candidate)
    if (structural["status"] != "pass" or operating["summary"]["effectiveErrorFindings"]
            or any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"])
            or overnight["status"] != "pass" or planning_validation["status"] != "pass"):
        raise ValueError("v1.2.1 ground-hold proposal failed validation")
    loads, connections = search.screen.allocate(search.screen.enumerate(candidate["legs"]))
    old = {l["id"]: l for l in search.base["legs"]}
    new = [l for l in candidate["legs"] if l["id"] not in old]
    ids = {l["id"] for l in new}
    frequency = Counter((l["origin"], l["destination"]) for l in search.base["legs"])
    after_frequency = Counter((l["origin"], l["destination"]) for l in candidate["legs"])
    new_rows = []
    for l in new:
        new_rows.append({**l, "originName": search.screen.cities[l["origin"]]["displayName"],
                         "destinationName": search.screen.cities[l["destination"]]["displayName"],
                         "originTimezone": search.screen.cities[l["origin"]]["timezone"],
                         "destinationTimezone": search.screen.cities[l["destination"]]["timezone"],
                         "blockMinutes": search.screen.utc(l)[2],
                         "localOpportunity": loads[l["id"]]["local"], "inboundOpportunity": loads[l["id"]]["inbound"],
                         "outboundOpportunity": loads[l["id"]]["outbound"], "throughOpportunity": loads[l["id"]]["through"],
                         "totalOpportunity": sum(loads[l["id"]].values()),
                         "connectingOdMarkets": len({(r["origin"], r["destination"]) for r in connections[l["id"]]}),
                         "beforeDepartures": frequency[l["origin"], l["destination"]],
                         "afterDepartures": after_frequency[l["origin"], l["destination"]]})
    holds = []
    services = []
    for route, (city, departure, back) in FLYING.items():
        sequence = sorted((l for l in search.base["legs"] if l["route"] == route), key=lambda l: l["sequenceWithinRoute"])
        a, b = HOLDS[route]
        before, following = sequence[a - 1], sequence[b - 1]
        hub = before["destination"]
        route_new = sorted((l for l in new if l["route"] == route), key=lambda l: l["sequenceWithinRoute"])
        following_after = next(l for l in candidate["legs"] if l["id"] == following["id"])
        old_interval = following["departureMinute"] - before["arrivalMinute"]
        new_interval = following_after["departureMinute"] - before["arrivalMinute"]
        block = sum(search.screen.utc(l)[2] for l in route_new)
        remaining = [route_new[0]["departureMinute"] - before["arrivalMinute"],
                     route_new[1]["departureMinute"] - route_new[0]["arrivalMinute"],
                     following_after["departureMinute"] - route_new[1]["arrivalMinute"]]
        holds.append({"route": route, "hub": hub, "line": before["line"], "day": before["day"], "fleet": before["fleet"],
                      "originalHoldMinutes": old_interval, "originalArrival": before["arrival"],
                      "originalDeparture": following["departure"], "newFollowingDeparture": following_after["departure"],
                      "addedBlockMinutes": block, "remainingGroundMinutes": new_interval - block,
                      "groundSegmentsMinutes": remaining,
                      "standClaimsBefore": sum(c["rowType"] == "stand" and c["label"] == str(route)
                                              for h in search.gates["cities"] for c in h["claims"]),
                      "standClaimsAfter": sum(c["rowType"] == "stand" and c["label"] == str(route)
                                             for h in gates["cities"] for c in h["claims"])})
        prior_legs = [l for l in search.base["legs"] if {l["origin"], l["destination"]} == {hub, city}]
        current_legs = [l for l in candidate["legs"] if {l["origin"], l["destination"]} == {hub, city}]
        original_after = sum(sum(loads[l["id"]].values()) for l in current_legs if l["id"] not in ids)
        prior = sum(sum(search.screen.loads[l["id"]].values()) for l in prior_legs)
        services.append({"hub": hub, "city": city, "beforeFromHub": frequency[hub, city],
                         "afterFromHub": after_frequency[hub, city], "beforeToHub": frequency[city, hub],
                         "afterToHub": after_frequency[city, hub],
                         "localOdBothDirections": search.screen.od[hub][city] + search.screen.od[city][hub],
                         "existingOpportunityBefore": prior, "existingOpportunityAfter": original_after})
    stands = [c for h in gates["cities"] for c in h["claims"] if c["rowType"] == "stand"]
    output = ROOT / "builds/schedule_7_v1_2_1_feasibility_01"
    report = {"scheduleId": candidate["schedule"]["id"], "status": "draft",
              "baseCanonical": {"filename": BASE, "sha256": sha256_file(ROOT / BASE)},
              "overlay": {"filename": OVERLAY, "sha256": sha256_file(ROOT / OVERLAY)},
              "demandId": search.screen.demand_id, "summary": {"legs": len(candidate["legs"]), "newLegs": len(new),
                  "routes": len({l["route"] for l in candidate["legs"]}), "lines": len({l["line"] for l in candidate["legs"]}),
                  "addedBlockMinutes": sum(r["blockMinutes"] for r in new_rows),
                  "effectiveOperatingErrors": operating["summary"]["effectiveErrorFindings"],
                  "effectiveOperatingWarnings": operating["summary"]["effectiveWarningFindings"],
                  "hardStopFailures": sum(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]),
                  "structuralStatus": structural["status"], "planningStatus": planning_validation["status"],
                  "overnightTurnFailures": len(overnight["findings"]), "standClaims": len(stands),
                  "standMinutes": sum(c["end"] - c["start"] for c in stands)},
              "model": "Uncapped full-CAA-capture O-D allocation over all zero-, one- and two-stop alternatives. Transfer waits 30–240 minutes, total circuity ≤2.25, connecting weights 0.35^stops / elapsed² / circuity². These are relative opportunity units, not loads or new travelers.",
              "holds": holds, "services": services, "newFlights": new_rows,
              "retimings": [{"flight": final["flight"], "origin": final["origin"], "destination": final["destination"],
                             "beforeDeparture": final["departure"], "beforeArrival": final["arrival"],
                             "afterDeparture": next(l["departure"] for l in candidate["legs"] if l["id"] == final["id"]),
                             "afterArrival": next(l["arrival"] for l in candidate["legs"] if l["id"] == final["id"])}],
              "connections": [{"newFlight": l["flight"], **r,
                               "flights": [next(x["flight"] for x in candidate["legs"] if x["id"] == identifier)
                                           for identifier in r["legs"]]}
                              for l in new for r in connections[l["id"]]]}
    # Compare one substitution at a time against the complete jointly allocated draft.
    # Timings come from the isolated screen; these comparisons are not a global optimum proof.
    report["alternatives"] = []
    for route, (city, departure, back) in COMPARISONS.items():
        selected = next(l for l in new if l["route"] == route)
        hub, fleet = selected["origin"], selected["fleet"]
        plan = {"legs": [search.leg(hub, city, departure, fleet), search.leg(city, hub, back, fleet)]}
        alternate = apply_optimization_overlay(search.base, search.overlay({**selections, route: plan}, [retiming]))
        alternate_operating = validate_operating_rules(alternate)
        alternate_loads, _ = search.screen.allocate(search.screen.enumerate(alternate["legs"]))
        alternate_new = [l for l in alternate["legs"] if l["id"] not in old]
        route_new = [l for l in alternate_new if l["route"] == route]
        report["alternatives"].append({"route": route, "city": city,
            "selectedCity": FLYING[route][0],
            "selectedLegOpportunities": [r["totalOpportunity"] for r in new_rows if r["route"] == route],
            "alternativeLegOpportunities": [sum(alternate_loads[l["id"]].values()) for l in route_new],
            "allNewLegOpportunity": sum(sum(alternate_loads[l["id"]].values()) for l in alternate_new),
            "effectiveOperatingErrors": alternate_operating["summary"]["effectiveErrorFindings"],
            "hardStopFailures": sum(c["hardStop"] and c["status"] == "fail" for c in alternate_operating["checks"]),
            "timings": [{"origin": l["origin"], "destination": l["destination"],
                         "departure": l["departure"], "arrival": l["arrival"]} for l in route_new]})
    for filename, value in {"canonical_schedule.json": candidate, "validation_report.json": structural,
                            "operating_validation_report.json": operating, "overnight_turn_validation.json": overnight,
                            "planning_snapshot.json": planning, "planning_validation_report.json": planning_validation,
                            "timetable.json": export_timetable(candidate), "gates.json": gates, "hold_analysis.json": report}.items():
        write_json(output / filename, value)
    return report


if __name__ == "__main__":
    report = build()
    print(report["summary"])
    for row in report["newFlights"]:
        print(row["flight"], row["route"], row["origin"], row["departure"], row["originTimezone"],
              row["destination"], row["arrival"], row["destinationTimezone"], round(row["totalOpportunity"], 1))
