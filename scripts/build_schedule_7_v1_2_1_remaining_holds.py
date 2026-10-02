"""Apply the second unpublished v1.2.1 round to the complete first-round draft."""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_1_remaining_holds import baseline, find_holds, ROUND_ONE
from caa_scheduler.io import write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.timetable import export_timetable

OVERLAY = "config/optimizations/schedule_7_v1_2_1_round_2.json"
FLYING = {118: ("BLV", 925, 1030), 151: ("XNA", 825, 938),
          147: ("PIT", 678, 784), 323: ("BWI", 1135, 1240)}
RETIMINGS = {1607: -3, 2043: 7}


def make_overlay(base):
    search = HoldSearch(base)
    holds = {h["route"]: h for h in find_holds(base)}
    selections = {}
    for route, (city, departure, back) in FLYING.items():
        hold = holds[route]
        selections[route] = {"legs": [search.leg(hold["hub"], city, departure, hold["fleet"]),
                                     search.leg(city, hold["hub"], back, hold["fleet"])]}
    retimings = []
    for flight, shift in RETIMINGS.items():
        leg = next(l for l in base["legs"] if l["flight"] == flight)
        retimings.append({"legId": leg["id"], "expectedDepartureMinute": leg["departureMinute"],
                         "expectedArrivalMinute": leg["arrivalMinute"],
                         "departureMinute": leg["departureMinute"] + shift,
                         "arrivalMinute": leg["arrivalMinute"] + shift,
                         "reason": "Minor timing alignment for additional flying in the remaining five-hour hub holds."})
    overlay = search.overlay(selections, retimings)
    overlay["id"] = "schedule-7-v1.2.1-ground-hold-round-2"
    overlay["schedule"].update(id="schedule_7_v1_2_1_feasibility_02", label="Schedule 7 v1.2.1 remaining hub-hold draft")
    overlay["baseSchedule"]["overlays"] = [ROUND_ONE]
    overlay["initiative"]["scope"] = "All remaining intra-route daytime hub/focus-city holds of at least 300 minutes. Add demand-supported low-frequency flying where feasible; keep v1.2.1 unpublished."
    overlay["initiative"]["selectionRationale"] = [
        "Add MCI-BLV third service and MCI-XNA second service, the leading feasible demand candidates for their hold slots.",
        "Add SYR-BWI second service on the late hold and SYR-PIT third service on the midday hold, avoiding two new BWI round trips.",
        "Leave Routes 322 and 122 unchanged: the feasible ABE loop has almost no outbound opportunity; strong alternatives fail timing, spacing or gate screens even with small following-flight shifts."]
    return overlay


def build():
    base = baseline()
    overlay = make_overlay(base)
    write_json(ROOT / OVERLAY, overlay)
    candidate = apply_optimization_overlay(base, overlay)
    structural = validate_schedule(candidate)
    operating = validate_operating_rules(candidate)
    overnight = validate_overnight_turns(candidate)
    planning = reconstruct_planning_snapshot(candidate)
    planning_validation = validate_planning_snapshot(planning, candidate)
    if structural["status"] != "pass" or operating["summary"]["effectiveErrorFindings"] or any(
            c["hardStop"] and c["status"] == "fail" for c in operating["checks"]) or overnight["status"] != "pass" or planning_validation["status"] != "pass":
        write_json(ROOT / "builds/schedule_7_v1_2_1_round_2_failure.json", {"structural": structural, "operating": operating, "overnight": overnight, "planning": planning_validation})
        raise ValueError("Remaining-hold draft failed validation; inspect the failure report")
    gates = export_gate_schedule(candidate)
    search = HoldSearch(base)
    loads, records = search.screen.allocate(search.screen.enumerate(candidate["legs"]))
    old = {l["id"]: l for l in base["legs"]}
    all_legs = {l["id"]: l for l in candidate["legs"]}
    new = [l for l in candidate["legs"] if l["id"] not in old]
    frequency = Counter((l["origin"], l["destination"]) for l in base["legs"])
    after_frequency = Counter((l["origin"], l["destination"]) for l in candidate["legs"])
    draft_legs = sorted((l for l in candidate["legs"] if l["id"].startswith("V121-R")), key=lambda l: l["flight"])
    released_frequency = Counter((l["origin"], l["destination"]) for l in base["legs"] if not l["id"].startswith("V121-R"))
    draft_flights = []
    for leg in draft_legs:
        draft_flights.append({**leg, "round": 2 if leg["id"] not in old else 1,
                       "originName": search.screen.cities[leg["origin"]]["displayName"],
                       "destinationName": search.screen.cities[leg["destination"]]["displayName"],
                       "originTimezone": search.screen.cities[leg["origin"]]["timezone"],
                       "destinationTimezone": search.screen.cities[leg["destination"]]["timezone"],
                       "blockMinutes": search.screen.utc(leg)[2],
                       "beforeDepartures": released_frequency[leg["origin"], leg["destination"]],
                       "afterDepartures": after_frequency[leg["origin"], leg["destination"]],
                       "localOpportunity": loads[leg["id"]]["local"],
                       "inboundOpportunity": loads[leg["id"]]["inbound"],
                       "outboundOpportunity": loads[leg["id"]]["outbound"],
                       "throughOpportunity": loads[leg["id"]]["through"],
                       "totalOpportunity": sum(loads[leg["id"]].values()),
                       "connectingOdMarkets": len({(r["origin"], r["destination"]) for r in records[leg["id"]]})})
    flights = [l for l in draft_flights if l["round"] == 2]
    holds = find_holds(base)
    for hold in holds:
        route = hold["route"]
        hold["status"] = "added" if route in FLYING else "deferred"
        route_new = sorted((l for l in new if l["route"] == route), key=lambda l: l["sequenceWithinRoute"])
        hold["addedBlockMinutes"] = sum(search.screen.utc(l)[2] for l in route_new)
        hold["newPairing"] = FLYING[route][0] if route in FLYING else ""
        before, following = all_legs[hold["beforeLegId"]], all_legs[hold["afterLegId"]]
        hold["groundSegmentsMinutes"] = [b["departureMinute"] - a["arrivalMinute"]
            for a, b in zip([before] + route_new, route_new + [following])]
        hold["remainingGroundMinutes"] = sum(hold["groundSegmentsMinutes"])
        hold["reason"] = ({322: "ABE is the only gate-screened candidate (0.7 outbound / 31.4 return opportunity). A stronger BWI loop fails full fixed-gate and passenger-touch validation.",
                           122: "No round trip fits unchanged clocks. A small delay to the SWF flight consumes its next minimum turn; delaying the SWF-DAY leg then misses DAY's bank."}.get(route)
                          or {118: "Leading MCI candidate; third BLV service.",
                              151: "Leading feasible MCI candidate; second XNA service.",
                              147: "PIT has balanced feed and leaves the one-flight BWI market for the late route.",
                              323: "Second BWI service. The return has modest feed and the 40-minute turns have little recovery margin."}[route])
    stands = [c for city in gates["cities"] for c in city["claims"] if c["rowType"] == "stand"]
    report = {"scheduleId": candidate["schedule"]["id"], "status": "draft", "baseScheduleId": base["schedule"]["id"],
              "overlay": {"filename": OVERLAY, "sha256": sha256_file(ROOT / OVERLAY)},
              "demandId": search.screen.demand_id,
              "summary": {"remainingHoldsBefore": len(holds), "treatedHolds": len(FLYING), "deferredHolds": len(holds) - len(FLYING),
                          "legs": len(candidate["legs"]), "newLegs": len(new), "cumulativeNewLegs": len(candidate["legs"]) - 1096,
                          "addedBlockMinutes": sum(l["blockMinutes"] for l in flights),
                          "cumulativeAddedBlockMinutes": sum(l["blockMinutes"] for l in draft_flights),
                          "effectiveOperatingErrors": operating["summary"]["effectiveErrorFindings"],
                          "effectiveOperatingWarnings": operating["summary"]["effectiveWarningFindings"],
                          "hardStopFailures": sum(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]),
                          "structuralStatus": structural["status"], "planningStatus": planning_validation["status"],
                          "overnightTurnFailures": len(overnight["findings"]), "standClaims": len(stands),
                          "standMinutes": sum(c["end"] - c["start"] for c in stands)},
              "holds": holds, "remainingHolds": find_holds(candidate), "newFlights": flights,
              "allDraftFlights": draft_flights,
              "retimings": [{"flight": flight, "origin": next(l["origin"] for l in base["legs"] if l["flight"] == flight),
                             "destination": next(l["destination"] for l in base["legs"] if l["flight"] == flight),
                             "shiftMinutes": shift,
                             "beforeDeparture": next(l["departure"] for l in base["legs"] if l["flight"] == flight),
                             "beforeArrival": next(l["arrival"] for l in base["legs"] if l["flight"] == flight),
                             "afterDeparture": next(l["departure"] for l in candidate["legs"] if l["flight"] == flight),
                             "afterArrival": next(l["arrival"] for l in candidate["legs"] if l["flight"] == flight)} for flight, shift in RETIMINGS.items()],
              "connections": [{"newFlight": leg["flight"], **r, "flights": [all_legs[i]["flight"] for i in r["legs"]]}
                              for leg in new for r in records[leg["id"]]],
              "allDraftConnections": [{"newFlight": leg["flight"], **r, "flights": [all_legs[i]["flight"] for i in r["legs"]]}
                                      for leg in draft_legs for r in records[leg["id"]]]}
    output = ROOT / "builds/schedule_7_v1_2_1_feasibility_02"
    for filename, value in {"canonical_schedule.json": candidate, "validation_report.json": structural,
                           "operating_validation_report.json": operating, "overnight_turn_validation.json": overnight,
                           "planning_snapshot.json": planning, "planning_validation_report.json": planning_validation,
                           "gates.json": gates, "timetable.json": export_timetable(candidate), "hold_analysis.json": report}.items():
        write_json(output / filename, value)
    return report


if __name__ == "__main__":
    report = build()
    print(report["summary"])
    for leg in report["newFlights"]:
        print(leg["route"], leg["flight"], leg["origin"], leg["departure"], leg["destination"], leg["arrival"], round(leg["totalOpportunity"], 1))
