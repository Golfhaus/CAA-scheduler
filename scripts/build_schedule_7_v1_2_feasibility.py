"""Build the unpublished v1.2 overlay chain from released v1.1.6."""
from collections import Counter, defaultdict
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.demand import load_demand_sources_from_manifest, parse_airport_od_matrix
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.timetable import export_timetable
from caa_scheduler.validation import validate_schedule

OVERLAYS = ["config/optimizations/schedule_7_v1_2_0_round_1.json"]
DEMAND_VERSION = "bts-db1c-6mo-jul2025-apr2026-v7"


def build():
    base_path = REPO_ROOT / "data/schedules/schedule_7_v1_1_6/canonical_schedule.json"
    candidate = read_json(base_path)
    pins = []
    for filename in OVERLAYS:
        path = REPO_ROOT / filename
        overlay = read_json(path)
        candidate = apply_optimization_overlay(candidate, overlay)
        pins.append({"filename": filename, "sha256": sha256_file(path)})
    assert candidate["schedule"]["status"] == "draft"
    structural = validate_schedule(candidate)
    operating = validate_operating_rules(candidate)
    planning = reconstruct_planning_snapshot(candidate, demand_data_version=DEMAND_VERSION)
    planning_validation = validate_planning_snapshot(planning, candidate)
    gates = export_gate_schedule(candidate)
    stands = [s for city in gates["cities"] for s in city["claims"] if s["rowType"] == "stand"]
    hard_stops = sum(c["hardStop"] and c["status"] == "fail" for c in operating["checks"])
    if (structural["status"] != "pass" or planning_validation["status"] != "pass"
            or operating["summary"]["effectiveErrorFindings"] or hard_stops):
        raise ValueError("Feasibility candidate failed validation")
    loaded = load_demand_sources_from_manifest(
        REPO_ROOT / "config/demand_data/bts_db1c_6mo_v7.json", REPO_ROOT)
    matrix = parse_airport_od_matrix(loaded["airportOdMatrixText"])
    frequency = Counter((l["origin"], l["destination"]) for l in candidate["legs"])
    lines = defaultdict(list)
    for leg in candidate["legs"]:
        if leg["fleet"] == "CRJ900":
            lines[leg["line"]].append(leg)
    ranking = []
    for line, legs in lines.items():
        days = len({l["route"] for l in legs})
        raw = sum(matrix["values"][l["origin"]][l["destination"]] for l in legs)
        shared = sum(matrix["values"][l["origin"]][l["destination"]]
                     / frequency[l["origin"], l["destination"]] for l in legs)
        rons = {max((l for l in legs if l["route"] == r),
                    key=lambda l: l["sequenceWithinRoute"])["destination"]
                for r in {l["route"] for l in legs}}
        hubs = set(candidate["operatingPolicy"]["hubs"] + candidate["operatingPolicy"]["focusCities"])
        if not (9 <= days <= 12 and rons & hubs):
            raise ValueError(f"Line {line} fails length or hub/focus-city RON requirement")
        ranking.append({"line": line, "routes": days, "legs": len(legs),
                        "averageMarketDemandPerRoute": round(raw / days, 3),
                        "averageMarketDemandPerLeg": round(raw / len(legs), 3),
                        "frequencyDividedOdPerRoute": round(shared / days, 3),
                        "frequencyDividedOdPerLeg": round(shared / len(legs), 3)})
    ranking.sort(key=lambda row: (-row["averageMarketDemandPerRoute"], row["line"]))
    summary = {"legs": len(candidate["legs"]),
               "routes": len({l["route"] for l in candidate["legs"]}),
               "lines": len({l["line"] for l in candidate["legs"]}),
               "effectiveOperatingErrors": operating["summary"]["effectiveErrorFindings"],
               "hardStopFailures": hard_stops, "standClaims": len(stands),
               "standMinutes": sum(s["end"] - s["start"] for s in stands)}
    report = {"scheduleId": candidate["schedule"]["id"], "status": "draft",
              "baseCanonical": {"filename": str(base_path.relative_to(REPO_ROOT)),
                                "sha256": sha256_file(base_path)},
              "overlays": pins, "summary": summary, "crj900DemandRanking": ranking,
              "demandInterpretation": "Directional daily market O&D, not predicted onboard loads; the frequency-divided comparison omits connections and assumes equal sharing."}
    output = REPO_ROOT / "builds" / candidate["schedule"]["id"]
    for filename, value in {"canonical_schedule.json": candidate,
                            "validation_report.json": structural,
                            "operating_validation_report.json": operating,
                            "planning_snapshot.json": planning,
                            "planning_validation_report.json": planning_validation,
                            "gates.json": gates, "timetable.json": export_timetable(candidate),
                            "feasibility_report.json": report}.items():
        write_json(output / filename, value)
    return report


if __name__ == "__main__":
    import json
    print(json.dumps(build(), indent=2))
