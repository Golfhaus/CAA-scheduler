from __future__ import annotations

from pathlib import Path
from typing import Any

from .importer import import_canonical_schedule
from .io import read_json, resolve_from_repo, write_json
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
    )
    timetable = export_timetable(canonical)
    validation = validate_schedule(canonical)
    expected = read_json(resolve_from_repo(repo_root, inputs["expectedTimetable"]))
    parity = timetable == expected

    write_json(output_directory / "canonical_schedule.json", canonical)
    write_json(
        output_directory / "timetable.json",
        timetable,
        indent=1,
        trailing_newline=False,
    )
    write_json(output_directory / "validation_report.json", validation)
    expected_bytes = resolve_from_repo(repo_root, inputs["expectedTimetable"]).read_bytes()
    generated_bytes = (output_directory / "timetable.json").read_bytes()

    return {
        "canonicalPath": output_directory / "canonical_schedule.json",
        "timetablePath": output_directory / "timetable.json",
        "validationPath": output_directory / "validation_report.json",
        "validation": validation,
        "timetableParity": parity,
        "timetableByteParity": generated_bytes == expected_bytes,
    }
