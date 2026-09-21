from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .allocation import build_frequency_fleet_plan_from_manifest
from .bank_placement import build_hub_bank_plan_from_manifest
from .bank_materialization import build_bank_materialization_diagnostic_from_manifest
from .build_config import validate_build_config
from .canonicalization import (
    build_canonical_schedule_from_exact_plan,
    sha256_json,
)
from .demand import build_demand_plan_from_manifest, resolve_demand_manifest
from .exact_materialization import (
    ExactGlobalRepairIncomplete,
    blocked_exact_materialization_plan,
    build_exact_materialization_plan_from_manifest,
)
from .gate_export import export_gate_schedule
from .io import read_json, resolve_from_repo, sha256_file, write_json
from .operating_validation import validate_operating_rules
from .planning import reconstruct_planning_snapshot, validate_planning_snapshot
from .routing import build_aircraft_route_plan_from_manifest
from .routing_repair import build_routing_repair_plan_from_manifest
from .timetable import export_timetable
from .validation import validate_schedule


GENERATED_FILENAMES = (
    "build_config.json",
    "build_report.json",
    "canonical_schedule.json",
    "validation_report.json",
    "operating_validation_report.json",
    "planning_snapshot.json",
    "planning_validation_report.json",
    "demand_plan.json",
    "frequency_fleet_plan.json",
    "hub_bank_plan.json",
    "aircraft_route_plan.json",
    "routing_repair_plan.json",
    "bank_materialization_diagnostic.json",
    "exact_materialization_plan.json",
    "canonicalization_report.json",
    "timetable.json",
    "gates.json",
)


def baseline_path_for(config: dict[str, Any], repo_root: Path) -> Path | None:
    starting_point = config.get("startingPoint", {})
    if starting_point.get("kind") != "previous_schedule":
        return None
    schedule_id = starting_point.get("scheduleId")
    if not schedule_id:
        return None
    return repo_root / "data" / "schedules" / schedule_id / "canonical_schedule.json"


def _apply_network_changes(
    candidate: dict[str, Any], changes: list[dict[str, Any]]
) -> list[str]:
    blockers = []
    city_by_code = {city["code"]: city for city in candidate["cities"]}
    removed: set[str] = set()
    for change in changes:
        airport = change["airport"].upper()
        action = change["action"]
        if action == "add":
            blockers.append(
                f"{airport}: airport additions require the network-planning and metadata stage"
            )
            continue
        city = city_by_code[airport]
        if action == "remove":
            if city["role"] in {"hub", "focus_city"}:
                blockers.append(
                    f"{airport}: removing a hub or focus city requires a revised operating-policy pin"
                )
                continue
            city["active"] = False
            city["role"] = "destination"
            removed.add(airport)
        elif action == "status_change":
            target = change["targetStatus"]
            if (
                target != "inactive"
                and target != city["role"]
                and ({target, city["role"]} & {"hub", "focus_city"})
            ):
                blockers.append(
                    f"{airport}: hub or focus-city role changes require a revised operating-policy pin"
                )
                continue
            if target == "inactive" and city["role"] in {"hub", "focus_city"}:
                blockers.append(
                    f"{airport}: deactivating a hub or focus city requires a revised operating-policy pin"
                )
                continue
            city["active"] = target != "inactive"
            if target != "inactive":
                city["role"] = target
            else:
                removed.add(airport)

    if removed:
        candidate["legs"] = [
            leg
            for leg in candidate["legs"]
            if leg["origin"] not in removed and leg["destination"] not in removed
        ]
        remaining_leg_ids = {leg["id"] for leg in candidate["legs"]}
        candidate["bankAssignments"] = [
            assignment
            for assignment in candidate.get("bankAssignments", [])
            if assignment["legId"] in remaining_leg_ids
        ]
        for airport in removed:
            candidate.get("gatePlan", {}).get("forcedStandSplits", {}).pop(
                airport, None
            )
    return blockers


def compile_candidate(
    config: dict[str, Any], baseline: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Compile a candidate from an explicit prior-schedule seed."""
    preflight = validate_build_config(config, baseline)
    report: dict[str, Any] = {
        "schemaVersion": "1.0.0",
        "buildId": config.get("buildId"),
        "sourceScheduleId": baseline.get("schedule", {}).get("id"),
        "status": "blocked_preflight" if preflight["status"] == "fail" else "compiling",
        "preflight": preflight,
        "blockers": [],
        "outputs": {},
    }
    if preflight["status"] == "fail":
        return None, report
    if config["startingPoint"]["kind"] == "blank":
        report["status"] = "blocked_planning_input"
        report["blockers"].append(
            "Blank-start construction requires the demand, network-planning, and routing stages"
        )
        return None, report

    candidate = copy.deepcopy(baseline)
    schedule = candidate["schedule"]
    schedule.update(
        {
            "id": config["buildId"],
            "number": config["schedule"]["number"],
            "version": config["schedule"]["version"],
            "label": config["schedule"]["label"],
            "status": "draft",
            "fleetCounts": copy.deepcopy(config["fleetCounts"]),
            "connectionWindowMinutes": copy.deepcopy(
                config["connectionWindowMinutes"]
            ),
        }
    )
    candidate["gatePlan"]["label"] = config["schedule"]["label"]
    planning_blockers = _apply_network_changes(
        candidate, config.get("networkChanges", [])
    )
    if planning_blockers:
        report["status"] = "blocked_planning_input"
        report["blockers"].extend(planning_blockers)
        return None, report

    structural = validate_schedule(candidate)
    operating = validate_operating_rules(candidate)
    planning = reconstruct_planning_snapshot(
        candidate,
        demand_data_version=config["inputs"]["demandData"]["version"],
    )
    planning_validation = validate_planning_snapshot(planning, candidate)
    hard_stops = [
        {
            "checkId": check["id"],
            "title": check["title"],
            "findingCount": check["metrics"].get("effectiveFindingCount", 0),
            "message": check["message"],
        }
        for check in operating["checks"]
        if check.get("hardStop") and check["status"] == "fail"
    ]
    report.update(
        {
            "status": "blocked_hard_stop"
            if hard_stops
            else (
                "candidate_ready"
                if structural["status"] == "pass"
                and operating["summary"]["effectiveErrorFindings"] == 0
                else "candidate_review_required"
            ),
            "structuralValidation": structural,
            "operatingValidation": operating,
            "planningSnapshot": planning,
            "planningValidation": planning_validation,
            "hardStops": hard_stops,
            "publicationReady": (
                not hard_stops
                and structural["status"] == "pass"
                and operating["summary"]["effectiveErrorFindings"] == 0
            ),
        }
    )
    return candidate, report


def build_candidate(
    config_path: Path,
    repo_root: Path,
    *,
    baseline_path: Path | None = None,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config_source = resolve_from_repo(repo_root, str(config_path)).resolve()
    config = read_json(config_source)
    baseline_source = baseline_path or baseline_path_for(config, repo_root)
    if baseline_source is None:
        baseline: dict[str, Any] = {
            "schedule": {},
            "cities": [],
            "provenance": {},
        }
    else:
        baseline = read_json(resolve_from_repo(repo_root, str(baseline_source)))

    destination = (
        resolve_from_repo(repo_root, str(output_directory)).resolve()
        if output_directory is not None
        else repo_root / "builds" / str(config.get("buildId", "invalid-build"))
    )
    candidate, report = compile_candidate(config, baseline)
    destination.mkdir(parents=True, exist_ok=True)
    for filename in GENERATED_FILENAMES:
        (destination / filename).unlink(missing_ok=True)
    report["outputDirectory"] = str(destination)
    report["outputs"] = {
        "buildConfig": "build_config.json",
        "buildReport": "build_report.json",
    }
    write_json(destination / "build_config.json", config)

    if candidate is None:
        write_json(destination / "build_report.json", report)
        return report

    try:
        demand_manifest = resolve_demand_manifest(
            repo_root, config["inputs"]["demandData"]["version"]
        )
        demand_plan = build_demand_plan_from_manifest(
            demand_manifest,
            repo_root,
            candidate["cities"],
            expected_hub_assignments={
                city["code"]: city["hubAssignments"]
                for city in candidate["cities"]
                if city["role"] != "hub"
            },
        )
        report["demandPlan"] = demand_plan
        if demand_plan["status"] == "fail":
            if report["status"] != "blocked_hard_stop":
                report["status"] = "blocked_planning_input"
            report["publicationReady"] = False
            report["blockers"].append(
                "The pinned demand plan does not cover the candidate network"
            )
        else:
            frequency_fleet_plan = build_frequency_fleet_plan_from_manifest(
                candidate,
                demand_plan,
                demand_manifest,
                repo_root,
            )
            report["frequencyFleetPlan"] = frequency_fleet_plan
            if frequency_fleet_plan["status"] == "fail":
                if report["status"] != "blocked_hard_stop":
                    report["status"] = "blocked_planning_input"
                report["publicationReady"] = False
                report["blockers"].append(
                    "The frequency and fleet plan does not satisfy planning constraints"
                )
            else:
                hub_bank_plan = build_hub_bank_plan_from_manifest(
                    candidate,
                    frequency_fleet_plan,
                    demand_manifest,
                    repo_root,
                )
                report["hubBankPlan"] = hub_bank_plan
                if hub_bank_plan["status"] == "fail":
                    curfew_check = next(
                        check
                        for check in hub_bank_plan["checks"]
                        if check["id"] == "curfew_enforcement"
                    )
                    if curfew_check["status"] == "fail":
                        report["status"] = "blocked_hard_stop"
                        report["hardStops"].append(
                            {
                                "checkId": "bank_curfew_enforcement",
                                "title": "Bank placement curfew enforcement",
                                "findingCount": hub_bank_plan["summary"]["curfewViolations"],
                                "message": curfew_check["message"],
                            }
                        )
                    elif report["status"] != "blocked_hard_stop":
                        report["status"] = "blocked_planning_input"
                    report["publicationReady"] = False
                    report["blockers"].append(
                        "The hub-bank plan cannot place every proposed hub flight"
                    )
                else:
                    aircraft_route_plan = build_aircraft_route_plan_from_manifest(
                        candidate,
                        frequency_fleet_plan,
                        hub_bank_plan,
                        demand_manifest,
                        repo_root,
                    )
                    report["aircraftRoutePlan"] = aircraft_route_plan
                    routing_repair_plan = build_routing_repair_plan_from_manifest(
                        candidate,
                        frequency_fleet_plan,
                        hub_bank_plan,
                        demand_manifest,
                        repo_root,
                    )
                    report["routingRepairPlan"] = routing_repair_plan
                    if routing_repair_plan["status"] == "fail":
                        curfew_check = next(
                            check
                            for check in routing_repair_plan["checks"]
                            if check["id"] == "curfew_enforcement"
                        )
                        if curfew_check["status"] == "fail":
                            report["status"] = "blocked_hard_stop"
                            report["hardStops"].append(
                                {
                                    "checkId": "routing_curfew_enforcement",
                                    "title": "Aircraft-routing curfew enforcement",
                                    "findingCount": routing_repair_plan["summary"][
                                        "curfewViolations"
                                    ],
                                    "message": curfew_check["message"],
                                }
                            )
                        elif report["status"] != "blocked_hard_stop":
                            report["status"] = "blocked_planning_input"
                        report["publicationReady"] = False
                        report["blockers"].append(
                            "The topology repair does not fit the selected fleet, "
                            "curfew, and RON constraints"
                        )
                    else:
                        materialization = build_bank_materialization_diagnostic_from_manifest(
                            candidate,
                            frequency_fleet_plan,
                            hub_bank_plan,
                            demand_manifest,
                            repo_root,
                        )
                        report["bankMaterializationDiagnostic"] = materialization
                        if report["status"] == "blocked_hard_stop":
                            report["blockers"].append(
                                "Exact materialization is suppressed until the candidate's hard stops are cleared"
                            )
                        else:
                            checkpoint_token = sha256_json(
                                {
                                    "candidate": candidate,
                                    "frequencyFleetPlan": frequency_fleet_plan,
                                    "hubBankPlan": hub_bank_plan,
                                    "routingRepairPlan": routing_repair_plan,
                                    "demandManifestSha256": sha256_file(
                                        demand_manifest
                                    ),
                                },
                                indent=None,
                            )[:16]
                            try:
                                exact_materialization = build_exact_materialization_plan_from_manifest(
                                    candidate,
                                    frequency_fleet_plan,
                                    hub_bank_plan,
                                    routing_repair_plan,
                                    demand_manifest,
                                    repo_root,
                                    seed_checkpoint_path=(
                                        destination
                                        / (
                                            ".exact_seed_checkpoint_"
                                            f"{checkpoint_token}.json"
                                        )
                                    ),
                                )
                            except (
                                ValueError,
                                ExactGlobalRepairIncomplete,
                            ) as error:
                                exact_materialization = blocked_exact_materialization_plan(
                                    candidate,
                                    frequency_fleet_plan,
                                    hub_bank_plan["planningRulesId"],
                                    str(error),
                                )
                            report["exactMaterializationPlan"] = exact_materialization
                            if exact_materialization["status"] != "pass":
                                report["status"] = "blocked_planning_input"
                                report["blockers"].append(
                                    exact_materialization["nextStep"]["message"]
                                )
                                report["publicationReady"] = False
                            else:
                                demand_manifest_document = read_json(demand_manifest)
                                planning_rules_source = demand_manifest_document[
                                    "sources"
                                ]["planningRules"]
                                construction_provenance = {
                                    "sourceKind": "deterministic_planner",
                                    "sourceScheduleId": baseline["schedule"]["id"],
                                    "buildConfig": {
                                        "filename": "build_config.json",
                                        "sha256": sha256_json(config, indent=2),
                                    },
                                    "demandData": {
                                        "id": demand_manifest_document["id"],
                                        "filename": str(
                                            demand_manifest.relative_to(repo_root)
                                        ),
                                        "sha256": sha256_file(demand_manifest),
                                    },
                                    "planningRules": {
                                        "id": exact_materialization[
                                            "planningRulesId"
                                        ],
                                        "filename": planning_rules_source["filename"],
                                        "sha256": planning_rules_source["sha256"],
                                    },
                                    "exactMaterialization": {
                                        "filename": "exact_materialization_plan.json",
                                        "sha256": sha256_json(
                                            exact_materialization, indent=None
                                        ),
                                    },
                                }
                                generated_candidate, canonicalization = (
                                    build_canonical_schedule_from_exact_plan(
                                        candidate,
                                        demand_plan,
                                        frequency_fleet_plan,
                                        hub_bank_plan,
                                        exact_materialization,
                                        construction_provenance,
                                    )
                                )
                                generated_candidate["gatePlan"][
                                    "fixedPhysicalInventory"
                                ] = bool(
                                    config.get("constructionPolicy", {}).get(
                                        "fixedPhysicalInventory", False
                                    )
                                )
                                report["canonicalization"] = canonicalization
                                report["seedStructuralValidation"] = report[
                                    "structuralValidation"
                                ]
                                report["seedOperatingValidation"] = report[
                                    "operatingValidation"
                                ]
                                candidate = generated_candidate
                                structural = validate_schedule(candidate)
                                operating = validate_operating_rules(candidate)
                                report["structuralValidation"] = structural
                                report["operatingValidation"] = operating
                                hard_stops = [
                                    {
                                        "checkId": check["id"],
                                        "title": check["title"],
                                        "findingCount": check["metrics"].get(
                                            "effectiveFindingCount", 0
                                        ),
                                        "message": check["message"],
                                    }
                                    for check in operating["checks"]
                                    if check.get("hardStop")
                                    and check["status"] == "fail"
                                ]
                                report["hardStops"] = hard_stops
                                if structural["status"] != "pass":
                                    report["status"] = "blocked_planning_input"
                                    report["blockers"].append(
                                        "Canonical identifier assignment failed structural validation"
                                    )
                                elif hard_stops:
                                    report["status"] = "blocked_hard_stop"
                                    report["blockers"].append(
                                        "The materialized canonical schedule violates a non-waivable hard stop"
                                    )
                                elif operating["summary"][
                                    "effectiveErrorFindings"
                                ]:
                                    report["status"] = "candidate_review_required"
                                else:
                                    report["status"] = "candidate_ready"
                                report["publicationReady"] = (
                                    structural["status"] == "pass"
                                    and not hard_stops
                                    and operating["summary"][
                                        "effectiveErrorFindings"
                                    ]
                                    == 0
                                )
    except ValueError as error:
        if report["status"] != "blocked_hard_stop":
            report["status"] = "blocked_planning_input"
        report["publicationReady"] = False
        report["blockers"].append(str(error))

    write_json(destination / "validation_report.json", report["structuralValidation"])
    write_json(
        destination / "operating_validation_report.json",
        report["operatingValidation"],
    )
    write_json(destination / "planning_snapshot.json", report["planningSnapshot"])
    write_json(
        destination / "planning_validation_report.json",
        report["planningValidation"],
    )
    if "demandPlan" in report:
        write_json(destination / "demand_plan.json", report["demandPlan"])
    if "frequencyFleetPlan" in report:
        write_json(
            destination / "frequency_fleet_plan.json",
            report["frequencyFleetPlan"],
        )
    if "hubBankPlan" in report:
        write_json(destination / "hub_bank_plan.json", report["hubBankPlan"])
    if "aircraftRoutePlan" in report:
        write_json(
            destination / "aircraft_route_plan.json",
            report["aircraftRoutePlan"],
        )
    if "routingRepairPlan" in report:
        write_json(
            destination / "routing_repair_plan.json",
            report["routingRepairPlan"],
            indent=None,
        )
    if "bankMaterializationDiagnostic" in report:
        write_json(
            destination / "bank_materialization_diagnostic.json",
            report["bankMaterializationDiagnostic"],
        )
    if "exactMaterializationPlan" in report:
        write_json(
            destination / "exact_materialization_plan.json",
            report["exactMaterializationPlan"],
            indent=None,
        )
    if "canonicalization" in report:
        write_json(
            destination / "canonicalization_report.json",
            report["canonicalization"],
        )
    report["outputs"].update(
        {
            "structuralValidation": "validation_report.json",
            "operatingValidation": "operating_validation_report.json",
            "planning": "planning_snapshot.json",
            "planningValidation": "planning_validation_report.json",
        }
    )
    if "demandPlan" in report:
        report["outputs"]["demandPlan"] = "demand_plan.json"
    if "frequencyFleetPlan" in report:
        report["outputs"]["frequencyFleetPlan"] = "frequency_fleet_plan.json"
    if "hubBankPlan" in report:
        report["outputs"]["hubBankPlan"] = "hub_bank_plan.json"
    if "aircraftRoutePlan" in report:
        report["outputs"]["aircraftRoutePlan"] = "aircraft_route_plan.json"
    if "routingRepairPlan" in report:
        report["outputs"]["routingRepairPlan"] = "routing_repair_plan.json"
    if "bankMaterializationDiagnostic" in report:
        report["outputs"]["bankMaterializationDiagnostic"] = (
            "bank_materialization_diagnostic.json"
        )
    if "exactMaterializationPlan" in report:
        report["outputs"]["exactMaterializationPlan"] = (
            "exact_materialization_plan.json"
        )
    if "canonicalization" in report:
        report["outputs"]["canonicalization"] = "canonicalization_report.json"

    if report["status"] in {"candidate_ready", "candidate_review_required"}:
        write_json(destination / "canonical_schedule.json", candidate)
        write_json(
            destination / "timetable.json",
            export_timetable(candidate),
            indent=1,
            trailing_newline=False,
        )
        write_json(
            destination / "gates.json",
            export_gate_schedule(candidate),
            indent=1,
            trailing_newline=False,
        )
        report["outputs"].update(
            {
                "canonical": "canonical_schedule.json",
                "timetable": "timetable.json",
                "gates": "gates.json",
            }
        )

    write_json(destination / "build_report.json", report)
    return report
