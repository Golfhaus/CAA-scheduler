from __future__ import annotations

import csv
import hashlib
from io import StringIO
from pathlib import Path
from typing import Any

from .io import read_json, resolve_from_repo, sha256_file
from .planning import compute_multihub_assignments


def resolve_demand_manifest(repo_root: Path, demand_version: str) -> Path:
    matches = []
    for path in sorted((repo_root / "config" / "demand_data").glob("*.json")):
        if read_json(path).get("id") == demand_version:
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(
            f"Demand-data version {demand_version!r} resolves to "
            f"{len(matches)} manifests; exactly one is required"
        )
    return matches[0]


def parse_airport_od_matrix(text: str) -> dict[str, Any]:
    """Parse the versioned CSV matrix without pandas or path-bound state."""
    rows = list(csv.reader(StringIO(text)))
    try:
        header_index = next(
            index
            for index, row in enumerate(rows)
            if row and row[0].strip() == "Origin \\ Dest"
        )
    except StopIteration as error:
        raise ValueError("Airport O-D matrix header was not found") from error

    title = rows[0][0].strip() if rows and rows[0] else ""
    description = " ".join(
        row[0].strip()
        for row in rows[1:header_index]
        if row and row[0].strip()
    )
    airports = [value.strip() for value in rows[header_index][1:]]
    if not airports or any(not code for code in airports):
        raise ValueError("Airport O-D matrix contains an empty destination code")
    if len(airports) != len(set(airports)):
        raise ValueError("Airport O-D matrix contains duplicate destination codes")

    values: dict[str, dict[str, float]] = {}
    for row in rows[header_index + 1 :]:
        if not row or not row[0].strip():
            continue
        origin = row[0].strip()
        if origin in values:
            raise ValueError(f"Airport O-D matrix contains duplicate origin {origin}")
        if len(row) != len(airports) + 1:
            raise ValueError(
                f"Airport O-D matrix row {origin} has {len(row) - 1} values; "
                f"expected {len(airports)}"
            )
        parsed = {}
        for destination, raw_value in zip(airports, row[1:]):
            value = raw_value.strip()
            if not value:
                if origin != destination:
                    raise ValueError(
                        f"Airport O-D matrix is blank for {origin}->{destination}"
                    )
                parsed[destination] = 0.0
                continue
            try:
                numeric = float(value)
            except ValueError as error:
                raise ValueError(
                    f"Airport O-D matrix is not numeric for {origin}->{destination}"
                ) from error
            if numeric < 0:
                raise ValueError(
                    f"Airport O-D matrix is negative for {origin}->{destination}"
                )
            parsed[destination] = numeric
        values[origin] = parsed

    if set(values) != set(airports):
        missing = sorted(set(airports) - set(values))
        extra = sorted(set(values) - set(airports))
        raise ValueError(
            f"Airport O-D matrix row/column codes differ; missing={missing}, extra={extra}"
        )
    market_sizes = {
        origin: round(sum(destinations.values()), 6)
        for origin, destinations in values.items()
    }
    return {
        "title": title,
        "description": description,
        "airports": airports,
        "values": values,
        "marketSizes": market_sizes,
        "directionalPassengersPerDay": round(sum(market_sizes.values()), 6),
    }


def build_demand_plan(
    matrix_text: str,
    cities: list[dict[str, Any]],
    intergroup_demand: dict[str, Any],
    planning_rules: dict[str, Any],
    *,
    demand_version: str,
    matrix_filename: str,
    expected_hub_assignments: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    matrix = parse_airport_od_matrix(matrix_text)
    active_codes = {city["code"] for city in cities if city.get("active")}
    known_codes = {city["code"] for city in cities}
    matrix_codes = set(matrix["airports"])
    missing = sorted(active_codes - matrix_codes)
    unknown = sorted(matrix_codes - known_codes)
    inactive = sorted(matrix_codes - active_codes)
    checks = [
        {
            "id": "active_city_coverage",
            "status": "pass" if not missing and not unknown else "fail",
            "message": (
                f"Airport O-D matrix covers all {len(active_codes)} active cities"
                if not missing and not unknown
                else f"Airport O-D roster mismatch; missing={missing}, unknown={unknown}"
            ),
            "metrics": {
                "activeCities": len(active_codes),
                "matrixAirports": len(matrix_codes),
                "missing": missing,
                "unknown": unknown,
                "inactiveRepresented": inactive,
            },
        }
    ]

    assignments = None
    parity = None
    if not missing and not unknown:
        assignments = compute_multihub_assignments(
            cities,
            intergroup_demand["records"],
            matrix["marketSizes"],
            planning_rules,
        )
        if expected_hub_assignments is not None:
            differences = []
            for city in assignments["cities"]:
                expected = expected_hub_assignments.get(city["code"])
                if expected != city["hubAssignments"]:
                    differences.append(
                        {
                            "code": city["code"],
                            "expected": expected,
                            "computed": city["hubAssignments"],
                        }
                    )
                city["expectedHubAssignments"] = expected
                city["matchesExpected"] = expected == city["hubAssignments"]
            parity = {
                "compared": len(assignments["cities"]),
                "matched": len(assignments["cities"]) - len(differences),
                "differences": differences,
            }
            checks.append(
                {
                    "id": "golden_hub_assignment_parity",
                    "status": "pass" if not differences else "fail",
                    "message": (
                        f"Computed hub assignments match all {parity['compared']} "
                        "non-hub cities"
                        if not differences
                        else f"{len(differences)} computed hub assignments differ"
                    ),
                    "metrics": parity,
                }
            )

    failed = sum(check["status"] == "fail" for check in checks)
    return {
        "schemaVersion": "1.0.0",
        "demandDataVersion": demand_version,
        "status": "pass" if failed == 0 else "fail",
        "provenance": {
            "airportOdMatrix": {
                "filename": matrix_filename,
                "sha256": hashlib.sha256(matrix_text.encode("utf-8")).hexdigest(),
            },
            "intergroupDemandId": intergroup_demand["id"],
            "planningRulesId": planning_rules["id"],
        },
        "matrix": {
            "title": matrix["title"],
            "description": matrix["description"],
            "airportCount": len(matrix["airports"]),
            "directionalCellCount": len(matrix["airports"]) ** 2,
            "directionalPassengersPerDay": matrix["directionalPassengersPerDay"],
        },
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
        },
        "checks": checks,
        "marketSizes": dict(sorted(matrix["marketSizes"].items())),
        "multiHubAssignments": assignments,
        "assignmentParity": parity,
    }


def build_demand_plan_from_manifest(
    manifest_path: Path,
    repo_root: Path,
    cities: list[dict[str, Any]],
    *,
    expected_hub_assignments: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    resolved_manifest = resolve_from_repo(repo_root, str(manifest_path)).resolve()
    manifest = read_json(resolved_manifest)
    sources = manifest["sources"]
    loaded: dict[str, tuple[Path, dict[str, Any]]] = {}
    for key in ("airportOdMatrix", "intergroupDemand", "planningRules"):
        source = sources[key]
        path = resolve_from_repo(repo_root, source["filename"])
        actual_sha = sha256_file(path)
        if actual_sha.lower() != source["sha256"].lower():
            raise ValueError(
                f"Demand source fingerprint mismatch for {source['filename']}"
            )
        loaded[key] = (path, source)

    matrix_path = loaded["airportOdMatrix"][0]
    plan = build_demand_plan(
        matrix_path.read_text(encoding="utf-8"),
        cities,
        read_json(loaded["intergroupDemand"][0]),
        read_json(loaded["planningRules"][0]),
        demand_version=manifest["id"],
        matrix_filename=loaded["airportOdMatrix"][1]["filename"],
        expected_hub_assignments=expected_hub_assignments,
    )
    try:
        manifest_label = resolved_manifest.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        manifest_label = str(resolved_manifest)
    plan["provenance"]["manifest"] = manifest_label
    plan["provenance"]["manifestSchemaVersion"] = manifest["schemaVersion"]
    return plan
