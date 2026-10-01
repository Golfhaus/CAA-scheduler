"""Build the requested additive two-aircraft-day JAX/DAY proposal, never publish."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_schedule_7_v1_2_hub_growth import baseline, DemandScreen
from build_schedule_7_v1_2_feasibility import build
from caa_scheduler.bank_placement import _block_minutes, TIMEZONE_OFFSETS
from caa_scheduler.io import read_json, write_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay

OVERLAY = "config/proposals/schedule_7_v1_2_0_two_day_growth.json"
SERVICE = {"JAX": ["SFB", "FLL", "PGD", "PIE", "SRQ"],
           "DAY": ["CMH", "CAK", "IND", "PIT", "RFD"]}
ROUTES = [
    [("SFB", "JAX", 270), ("JAX", "DAY", 375), ("DAY", "CAK", 550),
     ("CAK", "DAY", 642), ("DAY", "JAX", 734), ("JAX", "FLL", 890),
     ("FLL", "JAX", 1000), ("JAX", "DAY", 1116)],
    [("DAY", "JAX", 309), ("JAX", "DAY", 458), ("DAY", "CMH", 607),
     ("CMH", "DAY", 689), ("DAY", "IND", 800), ("IND", "DAY", 887),
     ("DAY", "JAX", 976), ("JAX", "SFB", 1127)],
]


class TwoStopScreen(DemandScreen):
    """Extend the comparison to all six-hub two-stop choices on both networks."""
    def enumerate(self, legs):
        options = super().enumerate(legs)
        departures, arrivals = defaultdict(list), defaultdict(list)
        clocks = {l["id"]: self.utc(l) for l in legs}
        for leg in legs:
            departures[leg["origin"]].append(leg)
            arrivals[leg["destination"]].append(leg)
        window = self.schedule["schedule"]["connectionWindowMinutes"]
        minimum, maximum = window["minimum"], window["maximum"]
        for middle in legs:
            h1, h2 = middle["origin"], middle["destination"]
            if h1 not in self.hubs or h2 not in self.hubs or h1 == h2:
                continue
            md, ma, mb = clocks[middle["id"]]
            left = [(first, (md - clocks[first["id"]][1]) % 1440)
                    for first in arrivals[h1] if first["origin"] != h2]
            right = [(last, (clocks[last["id"]][0] - ma) % 1440)
                     for last in departures[h2] if last["destination"] != h1]
            left = [(l, w) for l, w in left if minimum <= w <= maximum]
            right = [(l, w) for l, w in right if minimum <= w <= maximum]
            for first, wait1 in left:
                a = first["origin"]
                for last, wait2 in right:
                    b = last["destination"]
                    if len({a, h1, h2, b}) < 4:
                        continue
                    circuity = (self.distances[a, h1] + self.distances[h1, h2]
                                + self.distances[h2, b]) / self.distances[a, b]
                    if circuity > 2.25:
                        continue
                    elapsed = clocks[first["id"]][2] + wait1 + mb + wait2 + clocks[last["id"]][2]
                    options[a, b].append({"legs": (first["id"], middle["id"], last["id"]),
                        "weight": 0.35 ** 2 / elapsed ** 2 / circuity ** 2,
                        "elapsed": elapsed, "wait": wait1 + wait2,
                        "hubs": (h1, h2), "waits": (wait1, wait2), "circuity": circuity})
        return options

    def allocate(self, options):
        loads, records = defaultdict(Counter), defaultdict(list)
        for (a, b), choices in options.items():
            total_weight = sum(c["weight"] for c in choices)
            reconciliation = 0
            for choice in choices:
                opportunity = self.od[a][b] * choice["weight"] / total_weight
                reconciliation += opportunity
                count = len(choice["legs"])
                for i, identifier in enumerate(choice["legs"]):
                    side = ("local" if count == 1 else "outbound" if i == 0 else
                            "inbound" if i == count - 1 else "through")
                    loads[identifier][side] += opportunity
                    if count > 1 and opportunity > 0:
                        records[identifier].append({"origin": a, "destination": b,
                            "opportunity": opportunity, "stops": count - 1,
                            "side": side, "legs": choice["legs"], "elapsed": choice["elapsed"],
                            "hubs": choice.get("hubs", (choice.get("hub"),)),
                            "waits": choice.get("waits", (choice["wait"],))})
            assert abs(reconciliation - self.od[a][b]) < 1e-7
        return loads, records


def make_overlay(schedule, screen):
    additions, assignments = [], []
    for index, pairs in enumerate(ROUTES):
        legs = []
        for number, (origin, destination, departure) in enumerate(pairs, 1):
            block = _block_minutes(origin, destination, screen.profile, screen.cities)
            arrival = (departure - TIMEZONE_OFFSETS[screen.cities[origin]["timezone"]] + block
                       + TIMEZONE_OFFSETS[screen.cities[destination]["timezone"]]) % 1440
            identifier = f"V120-2MAX-D{index + 1}-{number}-{origin}-{destination}"
            legs.append({"id": identifier, "origin": origin, "destination": destination,
                         "departureMinute": departure, "arrivalMinute": arrival})
            for operation, city, minute in (("departure", origin, departure), ("arrival", destination, arrival)):
                if city not in screen.hubs or city == "BHM":
                    continue
                bank = next(b for b in schedule["hubBanks"] if b["hub"] == city
                            and b["startMinute"] <= minute < b["endMinute"])
                assignments.append({"legId": identifier, "operation": operation, "bankId": bank["id"]})
        additions.append({"route": 703 + index, "line": "A", "day": 3 + index, "fleet": "MAX9", "legs": legs})
    reassignments = [{"sourceRoute": l["route"], "expectedLine": l["line"], "expectedDay": l["day"],
                      "expectedFleet": "MAX9", "targetRoute": l["route"] + 2, "line": l["line"],
                      "day": l["day"] + 2 * (l["line"] == "A")}
                     for l in schedule["legs"] if l["fleet"] == "MAX9"
                     and l["sequenceWithinRoute"] == 1 and l["route"] >= 703]
    return {"schemaVersion": "1.0.0", "id": "schedule-7-v1.2.0-two-day-jax-day-growth",
        "baseSchedule": {"scheduleId": schedule["schedule"]["id"],
                         "overlays": [f"config/optimizations/schedule_7_v1_2_0_round_{n}.json" for n in (1, 2)]},
        "schedule": {"id": "schedule_7_v1_2_0_two_day_growth", "version": "1.2.0-two-day-growth",
                     "label": "Schedule 7 v1.2 two-day JAX/DAY growth draft", "status": "draft"},
        "initiative": {"kind": "two_spare_max9_additive_growth", "authorizedBy": "user",
            "authorizedScope": "Two additional active MAX9 aircraft-days from existing inventory, in one consecutive two-day Line A insertion.",
            "authorizedLineRouteCounts": [{"fleet": "MAX9", "line": "A", "routes": 13,
                "userInstruction": "take two spare MAX9s instead of one, and build a two-day sequence that can be inserted into line A somewhere"}],
            "principles": ["Give one-flight markets second service before adding to RFD's three flights.",
                "Raise DAY-JAX to four daily flights in each direction, including the existing CRJ700.",
                "Preserve every existing flight, fleet, time, pairing and bank assignment. Normalize route/day labels only.",
                "Preserve gate/stand inventories, bank windows, curfews and maintenance rules. Keep this draft unpublished."]},
        "routeReassignments": reassignments, "addRoutes": additions, "bankAssignmentsToAdd": assignments}


def analyze(schedule, screen, candidate, checkpoint):
    options = screen.enumerate(candidate["legs"])
    loads, connections = screen.allocate(options)
    old = {l["id"]: l for l in schedule["legs"]}
    new = [l for l in candidate["legs"] if l["id"] not in old]
    ids = {l["id"] for l in new}
    one_options = DemandScreen.enumerate(screen, candidate["legs"])
    one_loads, _ = DemandScreen.allocate(screen, one_options)
    rows = []
    all_legs = {l["id"]: l for l in candidate["legs"]}
    for l in new:
        previous = next((p for p in new if p["route"] == l["route"] and
                         p["sequenceWithinRoute"] == l["sequenceWithinRoute"] - 1), None)
        row = dict(l)
        row.update({"insertionDay": l["day"] - 2,
                    "originName": screen.cities[l["origin"]]["displayName"],
                    "destinationName": screen.cities[l["destination"]]["displayName"],
                    "blockMinutes": screen.utc(l)[2],
                    "groundMinutesBefore": (screen.utc(l)[0] - screen.utc(previous)[1]) % 1440 if previous else None,
                    "localOpportunity": loads[l["id"]]["local"], "inboundOpportunity": loads[l["id"]]["inbound"],
                    "outboundOpportunity": loads[l["id"]]["outbound"], "throughOpportunity": loads[l["id"]]["through"],
                    "totalOpportunity": sum(loads[l["id"]].values()),
                    "oneStopScreenOpportunity": sum(one_loads[l["id"]].values()),
                    "connectingOdMarkets": len({(c["origin"], c["destination"]) for c in connections[l["id"]]}),
                    "connectionOptions": len(connections[l["id"]]),
                    "twoStopOpportunity": sum(c["opportunity"] for c in connections[l["id"]] if c["stops"] == 2)})
        for operation in ("arrival", "departure"):
            row[operation + "Bank"] = next((a["bankId"] for a in candidate["bankAssignments"]
                if a["legId"] == l["id"] and a["operation"] == operation), "")
        rows.append(row)
    before_frequency = Counter((l["origin"], l["destination"]) for l in schedule["legs"])
    after_frequency = Counter((l["origin"], l["destination"]) for l in candidate["legs"])
    services = []
    for hub, destinations in SERVICE.items():
        for city in destinations:
            leg_ids = [l["id"] for l in candidate["legs"] if {l["origin"], l["destination"]} == {hub, city}]
            services.append({"hub": hub, "city": city, "cityName": screen.cities[city]["displayName"],
                "beforeFromHub": before_frequency[hub, city], "afterFromHub": after_frequency[hub, city],
                "beforeToHub": before_frequency[city, hub], "afterToHub": after_frequency[city, hub],
                "newConnectingOpportunity": sum(loads[i]["inbound"] + loads[i]["outbound"] + loads[i]["through"] for i in leg_ids if i in ids),
                "localOdBothDirections": screen.od[hub][city] + screen.od[city][hub]})
    unique = 0
    faster = 0
    for (a, b), choices in options.items():
        denominator = sum(c["weight"] for c in choices)
        unique += screen.od[a][b] * sum(c["weight"] for c in choices if ids.intersection(c["legs"])) / denominator
        prior = screen.options.get((a, b), [])
        if prior and min(c["elapsed"] for c in choices) < min(c["elapsed"] for c in prior):
            faster += 1
    trunk = []
    for l in candidate["legs"]:
        if {l["origin"], l["destination"]} == {"JAX", "DAY"}:
            trunk.append({**l, "added": l["id"] in ids, "totalOpportunity": sum(loads[l["id"]].values()),
                          "throughOpportunity": loads[l["id"]]["through"],
                          "baselineOpportunity": sum(screen.loads[l["id"]].values()) if l["id"] in old else None})
    details = [{"newFlight": l["flight"], "newLegId": l["id"], **record,
                "flights": [all_legs[i]["flight"] for i in record["legs"]]}
               for l in new for record in connections[l["id"]]]
    deployments = [{"city": city, "previousFleets": sorted({l["fleet"] for l in schedule["legs"]
                    if city in (l["origin"], l["destination"])}),
                    "runwayLengthFeet": screen.cities[city].get("runwayLengthFeet"),
                    "elevationFeet": screen.cities[city].get("elevationFeet")}
                   for city in sorted({c for l in new for c in (l["origin"], l["destination"])})
                   if not any(l["fleet"] == "MAX9" and city in (l["origin"], l["destination"])
                              for l in schedule["legs"])]
    return {"sourceScheduleId": schedule["schedule"]["id"], "scheduleId": candidate["schedule"]["id"],
        "demandId": screen.demand_id, "overlay": OVERLAY, "summary": checkpoint["summary"],
        "activeMax9Before": 21, "activeMax9After": 23, "max9Inventory": 35, "spareMax9After": 12,
        "model": {"maximumStops": 2, "hubs": sorted(screen.hubs), "minimumConnectionMinutes": 30,
                  "maximumConnectionMinutes": 240, "maximumCircuity": 2.25, "transferWeight": 0.35,
                  "description": "Full CAA capture and no seat caps. These are opportunity units, not forecast passenger loads.",
                  "twoStopAllocation": "The middle flight receives through opportunity once; its two connection ends are not double-counted."},
        "newLegs": rows, "services": services, "trunkFlights": sorted(trunk, key=lambda l: (l["origin"], l["departureMinute"])),
        "newMax9Airports": deployments,
        "connections": details, "uniqueAllocatedNewItineraryOpportunity": unique,
        "odMarketsWithFasterBestItinerary": faster,
        "lineLengthAuthorizations": checkpoint["lineLengthAuthorizations"]}


def main():
    schedule = baseline()
    screen = TwoStopScreen(schedule)
    overlay = make_overlay(schedule, screen)
    write_json(ROOT / OVERLAY, overlay)
    checkpoint = build(OVERLAY)
    candidate = read_json(ROOT / "builds" / checkpoint["scheduleId"] / "canonical_schedule.json")
    report = analyze(schedule, screen, candidate, checkpoint)
    write_json(ROOT / "builds" / checkpoint["scheduleId"] / "growth_analysis.json", report)
    print(json.dumps({"checkpoint": checkpoint["summary"], "services": report["services"],
                      "newLegs": [{"flight": l["flight"], "from": l["origin"], "to": l["destination"],
                                   "departure": l["departure"], "arrival": l["arrival"],
                                   "totalOpportunity": round(l["totalOpportunity"], 1),
                                   "throughOpportunity": round(l["throughOpportunity"], 1)} for l in report["newLegs"]]}, indent=2))


if __name__ == "__main__":
    main()
