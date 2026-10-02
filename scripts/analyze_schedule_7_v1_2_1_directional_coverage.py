"""Read-only directional clustering and timed alternate-hub coverage audit."""
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_schedule_7_v1_2_two_day_growth import TwoStopScreen
from analyze_schedule_7_v1_2_1_remaining_holds import baseline
from build_schedule_7_v1_2_1_remaining_holds import OVERLAY
from caa_scheduler.bank_placement import TIMEZONE_OFFSETS
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay

START, END, SLOT = 270, 1260, 180


def normalize(minute):
    return minute + 1440 if minute < 180 else minute


def clock(minute):
    return f"{minute // 60 % 24:02}:{minute % 60:02}"


def largest_gap(times):
    points = [START] + sorted(t for t in times if START < t < END) + [END]
    return max(zip(points, points[1:]), key=lambda p: p[1] - p[0])


def clusters(schedule):
    pairs = defaultdict(list)
    cities = {c["code"]: c for c in schedule["cities"]}
    for leg in schedule["legs"]:
        pairs[leg["origin"], leg["destination"]].append(normalize(leg["departureMinute"]))
    found = []
    for (a, b), times in sorted(pairs.items()):
        if a > b or not 2 <= len(times) <= 3 or not 2 <= len(pairs[b, a]) <= 3:
            continue
        back = pairs[b, a]
        span = max(max(times) - min(times), max(back) - min(back))
        separation = abs(median(times) - median(back))
        if span > 420 or separation < 360:
            continue
        gaps = [largest_gap(t)[1] - largest_gap(t)[0] for t in (times, back)]
        if min(gaps) < 360:
            continue
        hub = a if cities[a]["role"] in ("hub", "focus_city") else b
        if cities[hub]["role"] not in ("hub", "focus_city"):
            continue
        found.append({"pairing": f"{a}-{b}", "hub": hub, "spoke": b if hub == a else a,
                      "classification": "Strict cluster" if span <= 360 else "Broader cluster",
                      "maxClusterSpanMinutes": span, "medianSeparationMinutes": separation})
    return found


def rating(value):
    return "High" if value >= .8 - 1e-9 else "Moderate" if value >= .5 - 1e-9 else "Low"


def audit(schedule, slot_minutes=SLOT, additional_elapsed=120):
    screen = TwoStopScreen(schedule)
    cities, options = screen.cities, screen.options
    legs = {l["id"]: l for l in schedule["legs"]}
    pair_rows = clusters(schedule)
    pair_rows.append({"pairing": "PIT-SYR", "hub": "SYR", "spoke": "PIT", "classification": "Improved reference",
                      "maxClusterSpanMinutes": None, "medianSeparationMinutes": None})
    groups_primary = defaultdict(Counter)
    for c in cities.values():
        if c["role"] == "destination":
            groups_primary[c["group"]][c["hubAssignments"][0]] += 1
    cells, directions, groups = [], [], []
    for pair in pair_rows:
        hub, spoke = pair["hub"], pair["spoke"]
        pair["primaryGroups"] = [g for g, counts in groups_primary.items() if counts.most_common(1)[0][0] == hub]
        pair["flights"] = [{**l, "originTimezone": cities[l["origin"]]["timezone"]}
                          for l in schedule["legs"] if {l["origin"], l["destination"]} == {hub, spoke}]
        for side in ("Outbound from spoke", "Inbound to spoke"):
            outbound = side == "Outbound from spoke"
            direct = [l for l in schedule["legs"] if (l["origin"], l["destination"]) == ((spoke, hub) if outbound else (hub, spoke))]
            gap_start, gap_end = largest_gap([normalize(l["departureMinute"]) for l in direct])
            reference_gap = [gap_start, gap_end]
            if not outbound:
                # Match missing reference-hub departure periods to arrival periods at the spoke.
                arrival_shift = median(screen.utc(l)[2] for l in direct) + TIMEZONE_OFFSETS[cities[spoke]["timezone"]] - TIMEZONE_OFFSETS[cities[hub]["timezone"]]
                gap_start, gap_end = int(gap_start + arrival_shift), int(gap_end + arrival_shift)
            footprint = {l["destination"] if outbound else l["origin"] for l in schedule["legs"]
                         if (l["origin"] == hub if outbound else l["destination"] == hub)} - screen.hubs - {spoke}
            group_od = Counter()
            for city in footprint:
                group_od[cities[city]["group"]] += screen.od[spoke][city] if outbound else screen.od[city][spoke]
            key = f"{spoke}-{hub} / {'out' if outbound else 'in'}"
            total_od = sum(group_od.values())
            slots = [(start, min(start + slot_minutes, gap_end)) for start in range(gap_start, gap_end, slot_minutes)]
            departure_services = [l for l in schedule["legs"] if (l["origin"] == spoke if outbound else l["destination"] == spoke)
                                  and (l["destination"] if outbound else l["origin"]) in screen.hubs - {hub}]
            for city in sorted(footprint):
                a, b = (spoke, city) if outbound else (city, spoke)
                demand = screen.od[a][b]
                if demand <= 0:
                    continue
                choices = options.get((a, b), [])
                reference = [p for p in choices if len(p["legs"]) == 2 and p.get("hub") == hub]
                if reference:
                    benchmark = min(p["elapsed"] for p in reference)
                    benchmark_type = "Best timed reference-hub connection"
                else:
                    first = [l for l in schedule["legs"] if (l["origin"], l["destination"]) == (a, hub)]
                    last = [l for l in schedule["legs"] if (l["origin"], l["destination"]) == (hub, b)]
                    benchmark = min(screen.utc(l)[2] for l in first) + min(screen.utc(l)[2] for l in last) + 45
                    benchmark_type = "Reference-hub block sum + 45 min transfer"
                for start, end in slots:
                    alternates = []
                    for p in choices:
                        first, last = legs[p["legs"][0]], legs[p["legs"][-1]]
                        n = len(p["legs"])
                        if n > 1 and (first["destination"] if outbound else last["origin"]) == hub:
                            continue
                        dep = normalize(first["departureMinute"])
                        arrival = dep - TIMEZONE_OFFSETS[cities[a]["timezone"]] + p["elapsed"] + TIMEZONE_OFFSETS[cities[b]["timezone"]]
                        time = dep if outbound else arrival
                        if start <= time < end and p["elapsed"] <= benchmark + additional_elapsed:
                            alternates.append(p)
                    one = [p for p in alternates if len(p["legs"]) <= 2]
                    best = min(one or alternates, key=lambda p: p["elapsed"]) if alternates else None
                    level = "One-stop/direct" if one else "Two-stop only" if alternates else "Missing"
                    weight = demand * (end - start) / (gap_end - gap_start)
                    cells.append({"key": key, "pairing": pair["pairing"], "spoke": spoke, "hub": hub, "direction": side,
                                  "group": cities[city]["group"], "otherCity": city, "odOrigin": a, "odDestination": b,
                                  "slotStart": start, "slotEnd": end, "odDemand": demand, "weight": weight,
                                  "oneStopCoveredWeight": weight if one else 0,
                                  "upToTwoStopsCoveredWeight": weight if alternates else 0, "coverage": level,
                                  "bestFlights": [legs[i]["flight"] for i in best["legs"]] if best else [],
                                  "bestHubs": list(best.get("hubs", (best.get("hub"),))) if best and len(best["legs"]) > 1 else [],
                                  "bestElapsed": best["elapsed"] if best else None,
                                  "bestDeparture": legs[best["legs"][0]]["departure"] if best else "",
                                  "bestArrival": legs[best["legs"][-1]]["arrival"] if best else "",
                                  "originTimezone": cities[a]["timezone"], "destinationTimezone": cities[b]["timezone"],
                                  "benchmarkMinutes": benchmark, "benchmarkType": benchmark_type})
            relevant = [c for c in cells if c["key"] == key]
            denominator = sum(c["weight"] for c in relevant)
            strong = sum(c["oneStopCoveredWeight"] for c in relevant) / denominator
            expanded = sum(c["upToTwoStopsCoveredWeight"] for c in relevant) / denominator
            any_gap = sum(screen.od[c["odOrigin"]][c["odDestination"]] for c in
                          {c["otherCity"]: c for c in relevant if c["oneStopCoveredWeight"] > 0}.values()) / total_od
            row = {"key": key, "pairing": pair["pairing"], "hub": hub, "spoke": spoke, "direction": side,
                   "referenceDepartureGap": reference_gap, "gapStart": gap_start, "gapEnd": gap_end,
                   "gapMinutes": gap_end - gap_start, "gapClock": f"{clock(gap_start)}–{clock(gap_end)}",
                   "timezone": cities[spoke]["timezone"], "odDemand": total_od, "oneStopCoverage": strong,
                   "anyGapOneStopCoverage": any_gap,
                   "upToTwoStopsCoverage": expanded, "rating": rating(strong), "primaryGroups": pair["primaryGroups"],
                   "alternateHubServices": [{"flight": l["flight"], "origin": l["origin"], "departure": l["departure"],
                                             "destination": l["destination"], "arrival": l["arrival"]} for l in departure_services]}
            directions.append(row)
            group_rows = []
            for group, demand in sorted(group_od.items()):
                detail = [c for c in relevant if c["group"] == group]
                if not detail:
                    continue
                group_strong = sum(c["oneStopCoveredWeight"] for c in detail) / sum(c["weight"] for c in detail)
                expanded_group = sum(c["upToTwoStopsCoveredWeight"] for c in detail) / sum(c["weight"] for c in detail)
                any_group = sum(c["odDemand"] for c in {c["otherCity"]: c for c in detail
                                                       if c["oneStopCoveredWeight"] > 0}.values()) / demand
                gr = {"key": key, "group": group, "primaryGroup": group in pair["primaryGroups"], "odDemand": demand,
                      "demandShare": demand / total_od, "oneStopCoverage": group_strong,
                      "anyGapOneStopCoverage": any_group,
                      "upToTwoStopsCoverage": expanded_group, "rating": rating(group_strong)}
                groups.append(gr)
                group_rows.append(gr)
            row["weakGroups"] = [g for g in sorted(group_rows, key=lambda g: (-g["primaryGroup"], -g["odDemand"]))
                                 if g["oneStopCoverage"] < .5 and (g["primaryGroup"] or g["demandShare"] >= .05)]
    return {"scheduleId": schedule["schedule"]["id"], "demandId": screen.demand_id,
            "method": {"strictMaximumSpanMinutes": 360, "broaderMaximumSpanMinutes": 420, "minimumMedianSeparationMinutes": 360,
                       "operatingWindow": [START, END], "slotMinutes": slot_minutes, "additionalElapsedToleranceMinutes": additional_elapsed,
                       "ratings": "High ≥80%; Moderate ≥50%; Low <50%, based on one-stop/direct replacement coverage",
                       "description": "Coverage is duration- and O-D-weighted market/time-bin reachability, not passengers served. Daily O-D is assumed uniform across gap periods. Inbound periods are implied spoke arrival windows from missing hub departures. The reference-hub destination footprint defines comparable markets. One-stop/direct alternates are rated separately from two-stop rescue. Transfers 30–240 min and circuity ≤2.25. An alternate must be no more than 120 min slower than the reference-hub benchmark. No seat caps or fare model."},
            "pairings": pair_rows, "directions": directions, "groups": groups, "cells": cells}


def main():
    schedule = apply_optimization_overlay(baseline(), read_json(ROOT / OVERLAY))
    report = audit(schedule)
    published = read_json(ROOT / "data/schedules/schedule_7_v1_2_0/canonical_schedule.json")
    report["publishedClusters"] = clusters(published)
    report["source"] = {"publishedCanonicalSha256": sha256_file(ROOT / "data/schedules/schedule_7_v1_2_0/canonical_schedule.json"),
                        "draftOverlays": ["config/optimizations/schedule_7_v1_2_1_round_1.json", OVERLAY]}
    write_json(ROOT / "builds/schedule_7_v1_2_1_directional_coverage.json", report)
    for row in report["directions"]:
        print(row["key"], row["gapClock"], row["rating"], round(row["oneStopCoverage"] * 100, 1),
              "any-gap", round(row["anyGapOneStopCoverage"] * 100, 1),
              round(row["upToTwoStopsCoverage"] * 100, 1),
              [(g["group"], round(g["oneStopCoverage"] * 100, 1)) for g in row["weakGroups"]], flush=True)


if __name__ == "__main__":
    main()
