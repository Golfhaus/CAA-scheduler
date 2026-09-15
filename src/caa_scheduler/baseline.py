from __future__ import annotations

from pathlib import Path
from typing import Any

from .allocation import build_frequency_fleet_plan_from_manifest
from .bank_placement import build_hub_bank_plan_from_manifest
from .demand import build_demand_plan_from_manifest
from .importer import import_canonical_schedule
from .gate_export import export_gate_schedule
from .io import read_json, resolve_from_repo, write_json
from .operating_validation import validate_operating_rules
from .planning import reconstruct_planning_snapshot, validate_planning_snapshot
from .routing import build_aircraft_route_plan_from_manifest
from .timetable import export_timetable
from .validation import validate_schedule


def build_baseline(config_path: Path, repo_root: Path) -> dict[str, Any]:
    config = read_json(config_path)
    inputs = config["inputs"]
    output_directory = resolve_from_repo(repo_root, config["outputs"]["directory"])
    canonical = import_canonical_schedule(
        workbook_path=resolve_from_repo(repo_root, inputs["workbook"]),
        city_information_path=resolve_from_repo(repo_root, inputs["cityInformation"]),
        schedule=config["schedule"],
        connection_window=config["connectionWindowMinutes"],
        gate_plan=config["gatePlan"],
        gate_baseline_path=resolve_from_repo(repo_root, inputs["expectedGate"]),
        operating_policy_path=resolve_from_repo(repo_root, inputs["operatingPolicy"]),
    )
    timetable = export_timetable(canonical)
    gate_schedule = export_gate_schedule(canonical)
    validation = validate_schedule(canonical)
    operating_validation = validate_operating_rules(canonical)
    planning = reconstruct_planning_snapshot(
        canonical,
        demand_data_version=inputs.get("demandData", {}).get("version"),
    )
    planning_validation = validate_planning_snapshot(planning, canonical)
    demand_input = inputs["demandData"]
    demand_plan = build_demand_plan_from_manifest(
        Path(demand_input["manifest"]),
        repo_root,
        canonical["cities"],
        expected_hub_assignments={
            city["code"]: city["hubAssignments"]
            for city in canonical["cities"]
            if city["role"] != "hub"
        },
    )
    if demand_plan["demandDataVersion"] != demand_input["version"]:
        raise ValueError("Baseline demand-data version does not match its manifest")
    frequency_fleet_plan = build_frequency_fleet_plan_from_manifest(
        canonical,
        demand_plan,
        Path(demand_input["manifest"]),
        repo_root,
    )
    hub_bank_plan = build_hub_bank_plan_from_manifest(
        canonical,
        frequency_fleet_plan,
        Path(demand_input["manifest"]),
        repo_root,
    )
    aircraft_route_plan = build_aircraft_route_plan_from_manifest(
        canonical,
        frequency_fleet_plan,
        hub_bank_plan,
        Path(demand_input["manifest"]),
        repo_root,
    )
    expected = read_json(resolve_from_repo(repo_root, inputs["expectedTimetable"]))
    parity = timetable == expected
    expected_gate_path = resolve_from_repo(repo_root, inputs["expectedGate"])
    expected_gate = read_json(expected_gate_path)
    gate_parity = gate_schedule == expected_gate

    write_json(output_directory / "canonical_schedule.json", canonical)
    write_json(
        output_directory / "timetable.json",
        timetable,
        indent=1,
        trailing_newline=False,
    )
    write_json(
        output_directory / "gates.json",
        gate_schedule,
        indent=1,
        trailing_newline=False,
    )
    write_json(output_directory / "validation_report.json", validation)
    write_json(
        output_directory / "operating_validation_report.json",
        operating_validation,
    )
    write_json(output_directory / "planning_snapshot.json", planning)
    write_json(
        output_directory / "planning_validation_report.json",
        planning_validation,
    )
    write_json(output_directory / "demand_plan.json", demand_plan)
    write_json(
        output_directory / "frequency_fleet_plan.json",
        frequency_fleet_plan,
    )
    write_json(output_directory / "hub_bank_plan.json", hub_bank_plan)
    write_json(output_directory / "aircraft_route_plan.json", aircraft_route_plan)
    expected_bytes = resolve_from_repo(repo_root, inputs["expectedTimetable"]).read_bytes()
    generated_bytes = (output_directory / "timetable.json").read_bytes()
    expected_gate_bytes = expected_gate_path.read_bytes()
    generated_gate_bytes = (output_directory / "gates.json").read_bytes()

    return {
        "canonicalPath": output_directory / "canonical_schedule.json",
        "timetablePath": output_directory / "timetable.json",
        "gatePath": output_directory / "gates.json",
        "validationPath": output_directory / "validation_report.json",
        "operatingValidationPath": output_directory / "operating_validation_report.json",
        "planningPath": output_directory / "planning_snapshot.json",
        "planningValidationPath": output_directory / "planning_validation_report.json",
        "demandPlanPath": output_directory / "demand_plan.json",
        "frequencyFleetPlanPath": output_directory / "frequency_fleet_plan.json",
        "hubBankPlanPath": output_directory / "hub_bank_plan.json",
        "aircraftRoutePlanPath": output_directory / "aircraft_route_plan.json",
        "validation": validation,
        "operatingValidation": operating_validation,
        "planningValidation": planning_validation,
        "demandPlan": demand_plan,
        "frequencyFleetPlan": frequency_fleet_plan,
        "hubBankPlan": hub_bank_plan,
        "aircraftRoutePlan": aircraft_route_plan,
        "timetableParity": parity,
        "timetableByteParity": generated_bytes == expected_bytes,
        "gateParity": gate_parity,
        "gateByteParity": generated_gate_bytes == expected_gate_bytes,
    }
