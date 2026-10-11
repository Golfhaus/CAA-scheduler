"""Replay the accepted first v1.2.5 round; validate and save without publishing."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.timetable import export_timetable
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import validate, demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4 import cache_network
from analyze_schedule_7_v1_2_4_xna import maintenance
from review_crj200_line_alignment import routes, longest_gap

CONFIG = "config/optimizations/schedule_7_v1_2_5.json"


def same(actual, expected, path="review"):
    if isinstance(actual, (float, int)) and isinstance(expected, (float, int)):
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8), path
    elif isinstance(actual, dict) and isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for key in actual:
            same(actual[key], expected[key], path + "." + str(key))
    elif isinstance(actual, list) and isinstance(expected, list):
        assert len(actual) == len(expected), path
        for index, (a, b) in enumerate(zip(actual, expected)):
            same(a, b, path + "." + str(index))
    else:
        assert actual == expected, (path, actual, expected)


def main():
    config = read_json(ROOT / CONFIG)
    assert config["schedule"]["status"] == "draft"
    assert sha256_file(ROOT / config["baseCanonical"]) == config["baseCanonicalSha256"]
    assert sha256_file(ROOT / config["acceptedOverlay"]) == config["acceptedOverlaySha256"]
    base = read_json(ROOT / config["baseCanonical"])
    accepted = read_json(ROOT / config["acceptedOverlay"])
    sources = accepted["sourceProposals"]
    for source in sources:
        assert sha256_file(ROOT / source["path"]) == source["sha256"], source["path"]
    alignment, proposal, review = [read_json(ROOT / source["path"]) for source in sources]
    assert alignment["baseSchedule"]["sha256"] == config["baseCanonicalSha256"]
    assert proposal["baseSchedule"]["alignmentOverlaySha256"] == sources[0]["sha256"]
    assert accepted["schedule"] == config["schedule"]
    aligned = apply_optimization_overlay(base, alignment)
    # Verify the exact historical aligned serialization, without needing builds/.
    aligned_sha = hashlib.sha256((json.dumps(aligned, indent=2, ensure_ascii=False) + "\n").encode()).hexdigest()
    assert aligned_sha == proposal["baseSchedule"]["sha256"] == review["baseSha256"]
    sequential = apply_optimization_overlay(aligned, proposal)
    sequential["schedule"].update(config["schedule"])
    sequential["gatePlan"]["label"] = config["schedule"]["label"]
    trial = apply_optimization_overlay(base, accepted)
    assert sequential == trial, "Cumulative replay differs from the reviewed sequence"
    selected = next(q for q in review["candidates"] if q["id"] == config["reviewedCandidate"])

    old = {leg["id"]: leg for leg in aligned["legs"]}
    now = {leg["id"]: leg for leg in trial["legs"]}
    retimings = {change["legId"]: change for change in accepted["retimeLegs"]}
    inserted = {leg["id"] for leg in accepted["insertLegs"]}
    assert set(now) - set(old) == inserted
    for identifier, leg in old.items():
        expected = deepcopy(leg)
        if identifier in retimings:
            change = retimings[identifier]
            expected.update(departureMinute=change["departureMinute"], arrivalMinute=change["arrivalMinute"],
                            departure=now[identifier]["departure"], arrival=now[identifier]["arrival"])
        expected["sequenceWithinRoute"] = now[identifier]["sequenceWithinRoute"]
        assert now[identifier] == expected, identifier
    assert [now[leg["id"]]["flight"] for leg in accepted["insertLegs"]] == [2173, 2174, 2175, 2176]
    assert len(trial["legs"]) == 1174
    assert trial["schedule"]["fleetCounts"] == base["schedule"]["fleetCounts"]
    assert trial["operatingPolicy"] == base["operatingPolicy"], "New operating exception"
    assert trial["cities"] == base["cities"], "Physical inventory changed"

    line_proof = []
    rows = routes(trial)
    hubs = set(trial["operatingPolicy"]["hubs"] + trial["operatingPolicy"]["focusCities"])
    targets = set(trial["operatingPolicy"]["ronTargetCities"])
    for line in alignment["initiative"]["sourceLines"]:
        assert {leg["fleet"] for leg in base["legs"] if leg["line"] == line} == {"CRJ200"}
    for line in alignment["initiative"]["resultLines"]:
        days = sorted((legs for legs in rows.values() if legs[0]["line"] == line), key=lambda legs: legs[0]["day"])
        assert 9 <= len(days) <= 12
        assert [legs[0]["day"] for legs in days] == list(range(1, len(days) + 1))
        numbers = [legs[0]["route"] for legs in days]
        assert numbers == list(range(min(numbers), max(numbers) + 1))
        for current, following in zip(days, days[1:] + days[:1]):
            assert current[-1]["destination"] == following[0]["origin"]
        rons = [{"route": legs[0]["route"], "day": legs[0]["day"], "city": legs[-1]["destination"]} for legs in days]
        independent = [row for row in rons if row["city"] in hubs and row["route"] not in {125, 136}]
        assert independent
        worst = longest_gap([row["city"] in targets and row["route"] not in {125, 136} for row in rons])
        assert worst <= trial["operatingPolicy"]["rollingRonWindowDays"]
        line_proof.append({"line": line, "fleet": "CRJ200", "routes": len(days), "routeRange": [min(numbers), max(numbers)],
                           "independentHubOrFocusRons": independent, "maximumNonMxRunExcluding125And136": worst})
    assert len(rows) == 181 and len({leg["line"] for leg in trial["legs"]}) == 19
    print("Exact cumulative replay, flight preservation and independent maintenance validated", flush=True)

    search = HoldSearch(aligned)
    cache_network(search)
    validation, _ = validate(search, {**proposal, "schedule": config["schedule"]})
    assert good(validation), validation
    compact_validation = {k: v for k, v in validation.items() if k != "affectedStations"}
    same(compact_validation, selected["validation"])
    actual_demand = demand(search, trial, inserted)
    for flight in actual_demand["flights"]:
        references = flight.pop("connectingFlights")
        flight.update(connectingFlightCount=len(references), connectingFlightNumbers=[leg["flight"] for leg in references])
        flight["topMarkets"] = flight["topMarkets"][:5]
    same(actual_demand, selected["demand"])
    connection_audit = audit(search, trial)
    same(connection_audit, selected["audit"])
    options = search.screen.enumerate(trial["legs"])
    loads, records = search.screen.allocate(options)
    changed_flights = []
    for change in accepted["retimeLegs"]:
        identifier = change["legId"]
        before = {tuple(record["legs"]) for record in search.screen.connections[identifier]}
        after = {tuple(record["legs"]) for record in records[identifier]}
        changed_flights.append({"flight": old[identifier]["flight"], "beforeDeparture": old[identifier]["departure"],
                               "afterDeparture": now[identifier]["departure"], "lostConnectingChoices": len(before - after),
                               "addedConnectingChoices": len(after - before), "oldOpportunity": sum(search.screen.loads[identifier].values()),
                               "newOpportunity": sum(loads[identifier].values())})
    same(changed_flights, selected["changedFlights"])
    for line in ("AE", "AF"):
        detail = maintenance(trial, line)
        detail.pop("longestRun", None)
        same(detail, selected["maintenance"][line])
    print("Reviewed demand, retiming connections and complete network tradeoffs reproduced", flush=True)

    manifest_sha = sha256_file(ROOT / "web/schedules.json")
    trial["provenance"]["optimizationDraft"] = {
        "configuration": CONFIG, "configurationSha256": sha256_file(ROOT / CONFIG),
        "baseCanonical": config["baseCanonical"], "baseCanonicalSha256": config["baseCanonicalSha256"],
        "acceptedOverlay": config["acceptedOverlay"], "acceptedOverlaySha256": config["acceptedOverlaySha256"],
        "status": "draft; unpublished", "publication": "Reserved to user decision",
        "baseRelease": trial["provenance"].pop("optimizationRelease"),
    }
    operating = validate_operating_rules(trial)
    snapshot = reconstruct_planning_snapshot(trial)
    gates = export_gate_schedule(trial)
    artifacts = {"canonical_schedule.json": trial, "validation_report.json": validate_schedule(trial),
                 "operating_validation_report.json": operating, "overnight_turn_validation.json": validate_overnight_turns(trial),
                 "planning_snapshot.json": snapshot, "planning_validation_report.json": validate_planning_snapshot(snapshot, trial),
                 "gates.json": gates, "timetable.json": export_timetable(trial), "connection_audit.json": connection_audit}
    output = ROOT / config["outputDirectory"]
    for filename, artifact in artifacts.items():
        write_json(output / filename, artifact, indent=1 if filename in {"gates.json", "timetable.json"} else 2)
    report = {"status": "validated unpublished v1.2.5 draft", "version": "1.2.5", "acceptedRound": 1,
              "acceptedOverlay": config["acceptedOverlay"], "acceptedOverlaySha256": config["acceptedOverlaySha256"],
              "baseCanonical": config["baseCanonical"], "baseCanonicalSha256": config["baseCanonicalSha256"],
              "canonicalSha256": sha256_file(output / "canonical_schedule.json"), "approval": accepted["approval"],
              "summary": {"flights": 1174, "routes": 181, "lines": 19, "addedFlights": 4,
                          "addedFlightNumbers": [2173, 2174, 2175, 2176], "retimedReleasedFlights": [1503, 1873],
                          "unchangedReleasedFlightClocks": 1168, "selectedAircraftDays": 66, "fleetInventoryChanged": False,
                          "effectiveOperatingErrors": 0, "operatingWarnings": validation["operatingWarnings"],
                          "standClaims": validation["standClaims"], "standMinutes": validation["standMinutes"]},
              "validation": compact_validation, "lineProof": line_proof, "routeMapping": accepted["routeReassignments"],
              "demandModel": review["model"], "addedFlightDemand": actual_demand,
              "changedFlightConnections": changed_flights, "connectionTradeoff": connection_audit,
              "hubBankChanges": accepted["hubBankChanges"], "checks": {
                  "shaPinnedSourceReplay": "pass", "cumulativeEqualsSequential": "pass", "reviewReproduction": "pass",
                  "originalFlightPreservationAndOnlyTwoRetimings": "pass", "independentMaintenanceWithout125And136": "pass",
                  "noNewOperatingExceptions": "pass", "appManifestUnchanged": "pass"},
              "publication": "Unpublished; main branch and app default remain released v1.2.4",
              "limitations": ["Both return aircraft turns are exactly the 40-minute minimum.",
                              "Aircraft overnight feasibility does not establish a crew duty/rest plan.",
                              "TOL-HOU's fastest modeled itinerary increases three minutes; pinned O-D is zero."]}
    write_json(output / "draft_report.json", report)
    assert sha256_file(ROOT / "web/schedules.json") == manifest_sha
    print(report["summary"])
    print("SAVED: v1.2.5 draft only; no app publication")


if __name__ == "__main__":
    main()
