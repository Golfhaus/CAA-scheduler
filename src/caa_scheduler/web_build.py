from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .instructions import build_instruction_catalog
from .io import read_json, write_json


WEB_ASSETS = (
    "index.html",
    "styles.css",
    "app.mjs",
    "build-config.mjs",
    "favicon.svg",
    "coastal-american-logo.png",
)


def build_web_console(
    manifest_path: Path, repo_root: Path, output_directory: Path
) -> dict[str, Any]:
    """Assemble a static, deployable copy of the read-only web console."""
    repo_root = repo_root.resolve()
    manifest_path = manifest_path.resolve()
    output_directory = output_directory.resolve()
    if output_directory in {repo_root, repo_root.parent}:
        raise ValueError("Web output must be a dedicated directory")

    manifest = read_json(manifest_path)
    schedule_ids = [schedule["id"] for schedule in manifest["schedules"]]
    if len(schedule_ids) != len(set(schedule_ids)):
        raise ValueError("Web manifest contains duplicate schedule IDs")
    if manifest["defaultScheduleId"] not in schedule_ids:
        raise ValueError("Web manifest defaultScheduleId is not listed")

    source_directory = manifest_path.parent
    if output_directory.exists():
        shutil.rmtree(output_directory)
    output_directory.mkdir(parents=True)

    for asset in WEB_ASSETS:
        source = source_directory / asset
        if not source.is_file():
            raise ValueError(f"Web asset is missing: {source}")
        shutil.copy2(source, output_directory / asset)

    copied_data: set[str] = set()
    for schedule in manifest["schedules"]:
        for relative_path in schedule["files"].values():
            source = (repo_root / relative_path).resolve()
            if repo_root not in source.parents or not source.is_file():
                raise ValueError(f"Web data source is invalid: {relative_path}")
            destination = output_directory / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied_data.add(relative_path)

    instruction_config = manifest["instructions"]
    primary_instruction = (repo_root / instruction_config["source"]).resolve()
    addition_paths = [
        (repo_root / relative_path).resolve()
        for relative_path in instruction_config.get("additions", [])
    ]
    for source in [primary_instruction, *addition_paths]:
        if repo_root not in source.parents or not source.is_file():
            raise ValueError(f"Instruction source is invalid: {source}")
    catalog_relative_path = instruction_config["catalog"]
    catalog_destination = (output_directory / catalog_relative_path).resolve()
    if output_directory not in catalog_destination.parents:
        raise ValueError("Instruction catalog destination is invalid")
    catalog = build_instruction_catalog(
        primary_instruction,
        addition_paths,
        repo_root,
        instruction_config["version"],
    )
    write_json(catalog_destination, catalog)

    build_setup = manifest.get("buildSetup", {})
    build_schema_path = build_setup.get("schema")
    if not build_schema_path:
        raise ValueError("Web manifest buildSetup.schema is required")
    build_schema_source = (repo_root / build_schema_path).resolve()
    if repo_root not in build_schema_source.parents or not build_schema_source.is_file():
        raise ValueError(f"Build configuration schema is invalid: {build_schema_path}")
    build_schema_destination = (output_directory / build_schema_path).resolve()
    if output_directory not in build_schema_destination.parents:
        raise ValueError("Build configuration schema destination is invalid")
    build_schema_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build_schema_source, build_schema_destination)

    write_json(output_directory / "schedules.json", manifest)
    return {
        "outputDirectory": output_directory,
        "scheduleCount": len(schedule_ids),
        "dataFileCount": len(copied_data),
        "instructionEntryCount": len(catalog["entries"]),
    }
