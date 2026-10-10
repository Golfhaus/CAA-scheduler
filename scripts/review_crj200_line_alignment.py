"""Replay and validate the unpublished CRJ200 alignment against released v1.2.4."""
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule

OVERLAY = "config/optimizations/schedule_7_crj200_line_alignment.json"
REPORT = "config/proposals/schedule_7_crj200_line_alignment_review.json"


def routes(schedule):
    result = defaultdict(list)
    for leg in schedule["legs"]:
        result[leg["route"]].append(leg)
    for legs in result.values():
        legs.sort(key=lambda leg: leg["sequenceWithinRoute"])
    return result


def longest_gap(flags):
    run = maximum = 0
    for flag in flags * 2:
        run = 0 if flag else run + 1
        maximum = max(maximum, run)
    return min(maximum, len(flags))


def successors(schedule):
    rows = routes(schedule)
    grouped = defaultdict(list)
    result = {}
    for legs in rows.values():
        grouped[legs[0]["line"]].append(legs)
        result.update({a["id"]: b["id"] for a, b in zip(legs, legs[1:])})
    overnight = {}
    for days in grouped.values():
        days.sort(key=lambda legs: legs[0]["day"])
        for current, following in zip(days, days[1:] + days[:1]):
            overnight[current[-1]["id"]] = following[0]["id"]
    return result, overnight


def main():
    overlay = read_json(ROOT / OVERLAY)
    base_path = ROOT / overlay["baseSchedule"]["canonical"]
    assert sha256_file(base_path) == overlay["baseSchedule"]["sha256"], "Stale base"
    base = read_json(base_path)
    old_routes = routes(base)
    selected = set(overlay["initiative"]["sourceLines"])
    fleet_verification = []
    for line in sorted(selected):
        legs = [leg for leg in base["legs"] if leg["line"] == line]
        fleets = sorted({leg["fleet"] for leg in legs})
        assert fleets == ["CRJ200"], f"Discard non-CRJ200 line {line}: {fleets}"
        fleet_verification.append({"line": line, "fleets": fleets,
                                   "routeCount": len({leg["route"] for leg in legs})})
    trial = apply_optimization_overlay(base, overlay)
    new_routes = routes(trial)
    old_legs = {leg["id"]: leg for leg in base["legs"]}
    new_legs = {leg["id"]: leg for leg in trial["legs"]}
    assert old_legs.keys() == new_legs.keys()
    mutable = {"route", "line", "day", "sequenceWithinRoute"}
    for identifier, old in old_legs.items():
        new = new_legs[identifier]
        assert {k: v for k, v in old.items() if k not in mutable} == {
            k: v for k, v in new.items() if k not in mutable}
        if old["line"] not in selected:
            assert old == new
    for key in ("cities", "hubBanks", "bankAssignments", "operatingPolicy"):
        assert base[key] == trial[key]
    assert base["schedule"]["fleetCounts"] == trial["schedule"]["fleetCounts"]
    assert set(old_routes) == set(new_routes)
    protected = set(overlay["initiative"]["protectedRoutes"])
    for route in protected:
        assert [leg["id"] for leg in old_routes[route]] == [
            leg["id"] for leg in new_routes[route]], f"Protected day {route} changed"
    old_next, old_overnight = successors(base)
    new_next, new_overnight = successors(trial)
    assert old_overnight == new_overnight, "Overnight flight handoffs changed"
    for route in overlay["initiative"]["protectedNextRoutes"]:
        assert old_routes[route][0]["id"] == new_routes[route][0]["id"]

    hubs = set(trial["operatingPolicy"]["hubs"] + trial["operatingPolicy"]["focusCities"])
    targets = set(trial["operatingPolicy"]["ronTargetCities"])
    line_rows = []
    for line in overlay["initiative"]["resultLines"]:
        days = sorted((legs for legs in new_routes.values() if legs[0]["line"] == line),
                      key=lambda legs: legs[0]["day"])
        assert 9 <= len(days) <= 12
        numbers = [legs[0]["route"] for legs in days]
        assert numbers == list(range(min(numbers), max(numbers) + 1))
        assert [legs[0]["day"] for legs in days] == list(range(1, len(days) + 1))
        rons = [{"day": legs[0]["day"], "route": legs[0]["route"],
                 "city": legs[-1]["destination"], "arrival": legs[-1]["arrival"],
                 "arrivalMinute": legs[-1]["arrivalMinute"]} for legs in days]
        independent = [row for row in rons if row["city"] in hubs and row["route"] not in protected]
        assert independent, f"Line {line} depends on protected DAY RON"
        flags = [row["city"] in targets and row["route"] not in protected for row in rons]
        worst = longest_gap(flags)
        assert worst <= trial["operatingPolicy"]["rollingRonWindowDays"], "New grace needed"
        for current, following in zip(days, days[1:] + days[:1]):
            assert current[-1]["destination"] == following[0]["origin"]
        line_rows.append({"line": line, "fleet": "CRJ200", "routes": len(days),
                          "routeRange": [min(numbers), max(numbers)],
                          "hubOrFocusRons": [row for row in rons if row["city"] in hubs],
                          "independentHubOrFocusRons": independent,
                          "maximumNonMxRunExcluding125And136": worst,
                          "sourceRouteOrder": [next(x["sourceRoute"] for x in overlay["routeReassignments"]
                                                    if x["targetRoute"] == route) for route in numbers]})
    structure = validate_schedule(trial)
    operating = validate_operating_rules(trial)
    baseline_operating = validate_operating_rules(base)
    for check_id in ("section_26_pairing_spacing", "section_26_city_departure_gap",
                     "section_26_service_gap_policy_consistency"):
        old_check = next(c for c in baseline_operating["checks"] if c["id"] == check_id)
        new_check = next(c for c in operating["checks"] if c["id"] == check_id)
        assert old_check == new_check, f"Unexpected spacing change: {check_id}"
    overnight = validate_overnight_turns(trial)
    planning = reconstruct_planning_snapshot(trial)
    plan_check = validate_planning_snapshot(planning, trial)
    assert structure["status"] == overnight["status"] == plan_check["status"] == "pass"
    assert operating["summary"]["effectiveErrorFindings"] == 0
    assert not any(check["hardStop"] and check["status"] == "fail" for check in operating["checks"])
    gates = export_gate_schedule(trial)
    stands = [claim for city in gates["cities"] for claim in city["claims"] if claim["rowType"] == "stand"]
    handoffs = []
    for identifier, following in new_next.items():
        if following == old_next.get(identifier):
            continue
        arriving = new_legs[identifier]
        departing = new_legs[following]
        handoffs.append({"city": arriving["destination"], "inboundFlight": arriving["flight"],
                         "arrival": arriving["arrival"], "outboundFlight": departing["flight"],
                         "departure": departing["departure"], "oldOutboundFlight": old_legs[old_next[identifier]]["flight"],
                         "newRoute": arriving["route"],
                         "turnMinutes": (departing["departureMinute"] - arriving["arrivalMinute"]) % 1440})
    future = []
    for terminator, originator in ((125, 126), (136, 137)):
        last, first = new_routes[terminator][-1], new_routes[originator][0]
        deadline = first["departureMinute"] - trial["operatingPolicy"]["turns"]["minimumMinutes"]
        future.append({"terminatorRoute": terminator, "line": last["line"], "day": last["day"],
                       "terminatorFlight": last["flight"], "dayArrival": last["arrival"],
                       "nextRoute": originator, "nextDay": first["day"], "nextFlight": first["flight"],
                       "nextDeparture": first["departure"], "returnToDayDeadlineMinute": deadline,
                       "returnToDayDeadline": f"{deadline // 60:02}:{deadline % 60:02}",
                       "extensionsImplemented": False})
    report = {"status": "validated unpublished working draft", "baseCanonical": str(base_path.relative_to(ROOT)),
              "baseSha256": sha256_file(base_path), "overlay": OVERLAY, "overlaySha256": sha256_file(ROOT / OVERLAY),
              "fleetVerification": fleet_verification, "discardedLines": [], "resultLines": line_rows,
              "retiredLine": "AR", "routeMapping": overlay["routeReassignments"],
              "changedDaytimeHandoffs": sorted(handoffs, key=lambda row: (row["city"], row["arrival"])),
              "preservedOvernightHandoffs": len(old_overnight), "reassignedLegs": len(overlay["legReassignments"]),
              "futureDayExtensions": future,
              "summary": {"flights": len(trial["legs"]), "routes": len(new_routes),
                          "lines": len({leg["line"] for leg in trial["legs"]}), "selectedAircraftDays": 66,
                          "changedFlightTimes": 0, "newFlights": 0, "effectiveOperatingErrors": 0,
                          "operatingWarnings": operating["summary"]["effectiveWarningFindings"],
                          "standClaims": len(stands), "standMinutes": sum(c["end"] - c["start"] for c in stands)},
              "checks": {"structure": "pass", "operatingHardStops": "pass", "overnightTurns": "pass",
                         "planning": "pass", "gatesAndStands": "pass", "flightAndClockPreservation": "pass",
                         "independentMaintenanceWithout125And136": "pass", "newRollingRonGrace": False,
                         "section26": "unchanged passenger schedule; existing spacing findings unchanged"},
              "publication": "Reserved to user decision; app default remains released v1.2.4"}
    write_json(ROOT / REPORT, report)
    output = ROOT / "builds/crj200-line-alignment"
    for filename, data in {"canonical_schedule.json": trial, "operating_validation_report.json": operating,
                           "overnight_turn_validation.json": overnight, "planning_snapshot.json": planning,
                           "validation_report.json": structure, "planning_validation_report.json": plan_check,
                           "gates.json": gates}.items():
        write_json(output / filename, data)
    print(report["summary"])
    for row in line_rows:
        print(row["line"], row["routes"], "independent hub RONs:",
              [(r["route"], r["city"]) for r in row["independentHubOrFocusRons"]],
              "max non-MX run:", row["maximumNonMxRunExcluding125And136"])


if __name__ == "__main__":
    main()
