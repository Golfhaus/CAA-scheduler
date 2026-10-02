"""Discover every remaining daytime hub/focus-city hold of at least five hours."""
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_schedule_7_v1_2_1_holds import BASE, HoldSearch
from caa_scheduler.io import read_json, write_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay

ROUND_ONE = "config/optimizations/schedule_7_v1_2_1_round_1.json"


def baseline():
    return apply_optimization_overlay(read_json(ROOT / BASE), read_json(ROOT / ROUND_ONE))


def find_holds(schedule, minimum=300):
    hubs = {c["code"] for c in schedule["cities"] if c["role"] in ("hub", "focus_city")}
    routes = defaultdict(list)
    for leg in schedule["legs"]:
        routes[leg["route"]].append(leg)
    holds = []
    for route, legs in sorted(routes.items()):
        legs.sort(key=lambda l: l["sequenceWithinRoute"])
        for before, after in zip(legs, legs[1:]):
            gap = (after["departureMinute"] - before["arrivalMinute"]) % 1440
            if before["destination"] in hubs and gap >= minimum:
                holds.append({"route": route, "hub": before["destination"], "fleet": before["fleet"],
                              "line": before["line"], "day": before["day"],
                              "arrival": before["arrival"], "departure": after["departure"],
                              "holdMinutes": gap, "beforeLegId": before["id"], "afterLegId": after["id"],
                              "sequences": [before["sequenceWithinRoute"], after["sequenceWithinRoute"]]})
    return sorted(holds, key=lambda h: (-h["holdMinutes"], h["route"]))


def main():
    base = baseline()
    search = HoldSearch(base)
    reports = []
    for hold in find_holds(base):
        report = search.search(hold["route"], hold=hold["sequences"])
        reports.append({**hold, "candidateTimings": report["candidateTimings"],
                        "markets": report["markets"], "plans": report["plans"]})
        print(hold["route"], hold["hub"], hold["arrival"], hold["departure"], hold["holdMinutes"],
              [(p["city"], round(p["score"], 1), [round(v, 1) for v in p["legScores"]]) for p in report["plans"][:8]], flush=True)
    write_json(ROOT / "builds/schedule_7_v1_2_1_remaining_hold_search.json",
               {"baseScheduleId": base["schedule"]["id"], "holds": reports})


if __name__ == "__main__":
    main()
