from __future__ import annotations

from pathlib import Path
from typing import Any

from .importer import import_canonical_schedule
from .gate_export import export_gate_schedule
from .io import read_json, resolve_from_repo, write_json
from .operating_validation import validate_operating_rules
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
        "validation": validation,
        "operatingValidation": operating_validation,
        "timetableParity": parity,
        "timetableByteParity": generated_bytes == expected_bytes,
        "gateParity": gate_parity,
        "gateByteParity": generated_gate_bytes == expected_gate_bytes,
    }
