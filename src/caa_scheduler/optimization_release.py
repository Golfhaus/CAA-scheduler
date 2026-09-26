from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .gate_export import export_gate_schedule
from .io import read_json, sha256_file, write_json
from .operating_validation import validate_operating_rules
from .optimization_overlay import apply_optimization_overlay
from .planning import reconstruct_planning_snapshot, validate_planning_snapshot
from .timetable import export_timetable
from .validation import validate_schedule


def audit_hub_connections(
    canonical: dict[str, Any],
    *,
    hub: str,
    groups: dict[str, list[str]],
) -> dict[str, Any]:
    """Audit directional, one-stop connections between two city groups."""

    if len(groups) != 2:
        raise ValueError("Connection audit requires exactly two city groups")
    group_items = list(groups.items())
    minimum = canonical["schedule"]["connectionWindowMinutes"]["minimum"]
    maximum = canonical["schedule"]["connectionWindowMinutes"]["maximum"]
    legs = canonical["legs"]

    inbound = {
        city: [
            leg
            for leg in legs
            if leg["origin"] == city and leg["destination"] == hub
        ]
        for cities in groups.values()
        for city in cities
    }
    outbound = {
        city: [
            leg
            for leg in legs
            if leg["origin"] == hub and leg["destination"] == city
        ]
        for cities in groups.values()
        for city in cities
    }

    direct_rows = [
        {
            "city": city,
            "group": group,
            "toHubLegs": len(inbound[city]),
            "fromHubLegs": len(outbound[city]),
            "roundTripCovered": bool(inbound[city] and outbound[city]),
        }
        for group, cities in group_items
        for city in cities
    ]

    pairs = []
    for source_group, source_cities in group_items:
        destination_group, destination_cities = next(
            item for item in group_items if item[0] != source_group
        )
        for source in source_cities:
            for destination in destination_cities:
                options = []
                for arriving in inbound[source]:
                    for departing in outbound[destination]:
                        wait = (
                            int(departing["departureMinute"])
                            - int(arriving["arrivalMinute"])
                        ) % 1440
                        if minimum <= wait <= maximum:
                            options.append(
                                {
                                    "inboundLegId": arriving["id"],
                                    "inboundFlight": arriving["flight"],
                                    "hubArrival": arriving["arrival"],
                                    "outboundLegId": departing["id"],
                                    "outboundFlight": departing["flight"],
                                    "hubDeparture": departing["departure"],
                                    "waitMinutes": wait,
                                }
                            )
                options.sort(
                    key=lambda item: (
                        item["waitMinutes"],
                        item["inboundFlight"],
                        item["outboundFlight"],
                    )
                )
                pairs.append(
                    {
                        "source": source,
                        "sourceGroup": source_group,
                        "destination": destination,
                        "destinationGroup": destination_group,
                        "status": "connected" if options else "not_connected",
                        "options": options,
                    }
                )

    connected = sum(row["status"] == "connected" for row in pairs)
    coverage_by_source_group = {
        group: {
            "directionalPairs": sum(
                row["sourceGroup"] == group for row in pairs
            ),
            "connectedDirectionalPairs": sum(
                row["sourceGroup"] == group and row["status"] == "connected"
                for row in pairs
            ),
        }
        for group in groups
    }
    for row in coverage_by_source_group.values():
        row["missingDirectionalPairs"] = (
            row["directionalPairs"] - row["connectedDirectionalPairs"]
        )
    direct_covered = sum(row["roundTripCovered"] for row in direct_rows)
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "hub": hub,
        "connectionWindowMinutes": {"minimum": minimum, "maximum": maximum},
        "groups": copy.deepcopy(groups),
        "summary": {
            "targetCities": len(direct_rows),
            "directRoundTripCities": direct_covered,
            "directionalPairs": len(pairs),
            "connectedDirectionalPairs": connected,
            "missingDirectionalPairs": len(pairs) - connected,
            "connectionCoverage": round(connected / len(pairs), 6) if pairs else 0,
            "bySourceGroup": coverage_by_source_group,
        },
        "directCoverage": direct_rows,
        "directionalPairs": pairs,
    }


def build_optimization_release(
    config_path: Path,
    repo_root: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    """Build authoritative release artifacts from a guarded overlay chain."""

    repo_root = repo_root.resolve()
    config_path = config_path.resolve()
    config = read_json(config_path)
    base_path = (repo_root / config["baseCanonical"]).resolve()
    canonical = read_json(base_path)
    overlay_pins = []
    for relative_path in config["overlays"]:
        overlay_path = (repo_root / relative_path).resolve()
        overlay = read_json(overlay_path)
        canonical = apply_optimization_overlay(canonical, overlay)
        overlay_pins.append(
            {
                "id": overlay["id"],
                "filename": relative_path,
                "sha256": sha256_file(overlay_path),
            }
        )

    canonical["schedule"].update(copy.deepcopy(config["schedule"]))
    canonical["gatePlan"]["label"] = canonical["schedule"]["label"]
    canonical.setdefault("provenance", {})["optimizationRelease"] = {
        "sourceScheduleId": config["sourceScheduleId"],
        "config": {
            "filename": str(config_path.relative_to(repo_root)),
            "sha256": sha256_file(config_path),
        },
        "overlays": overlay_pins,
    }

    structural = validate_schedule(canonical)
    operating = validate_operating_rules(canonical)
    planning = reconstruct_planning_snapshot(
        canonical,
        demand_data_version=config.get("demandDataVersion"),
    )
    planning_validation = validate_planning_snapshot(planning, canonical)
    timetable = export_timetable(canonical)
    gates = export_gate_schedule(
        canonical,
        rejoin_avoidable_tows=config.get("rejoinAvoidableTows", True),
    )
    connection_audit = audit_hub_connections(
        canonical,
        hub=config["connectionAudit"]["hub"],
        groups=config["connectionAudit"]["groups"],
    )
    stand_claims = [
        claim
        for city in gates["cities"]
        for claim in city["claims"]
        if claim["rowType"] == "stand"
    ]
    audit_hub = config["connectionAudit"]["hub"]
    hub_gates = next(city for city in gates["cities"] if city["code"] == audit_hub)
    hub_stand_claims = [
        claim for claim in hub_gates["claims"] if claim["rowType"] == "stand"
    ]

    actual = {
        "legs": len(canonical["legs"]),
        "routes": len({leg["route"] for leg in canonical["legs"]}),
        "lines": len({leg["line"] for leg in canonical["legs"]}),
        "effectiveOperatingErrors": operating["summary"][
            "effectiveErrorFindings"
        ],
        "hardStopFailures": sum(
            check["hardStop"] and check["status"] == "fail"
            for check in operating["checks"]
        ),
        "directRoundTripCities": connection_audit["summary"][
            "directRoundTripCities"
        ],
        "connectedDirectionalPairs": connection_audit["summary"][
            "connectedDirectionalPairs"
        ],
        "standClaims": len(stand_claims),
        "standMinutes": sum(
            claim["end"] - claim["start"] for claim in stand_claims
        ),
        "hubStandClaims": len(hub_stand_claims),
        "hubStandMinutes": sum(
            claim["end"] - claim["start"] for claim in hub_stand_claims
        ),
    }
    expected = config.get("expectedRelease", {})
    mismatches = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise ValueError(f"Optimization release expectations changed: {mismatches}")

    if structural["status"] != "pass":
        raise ValueError("Optimization release failed structural validation")
    if operating["summary"]["effectiveErrorFindings"]:
        raise ValueError("Optimization release has effective operating errors")
    if actual["hardStopFailures"]:
        raise ValueError("Optimization release has hard-stop failures")
    if planning_validation["status"] != "pass":
        raise ValueError("Optimization release planning reconstruction failed")

    output = (
        output_directory.resolve()
        if output_directory is not None
        else (repo_root / config["outputDirectory"]).resolve()
    )
    if output != repo_root and repo_root not in output.parents:
        raise ValueError("Optimization release output must remain inside the repository")

    artifacts = {
        "canonical_schedule.json": canonical,
        "validation_report.json": structural,
        "operating_validation_report.json": operating,
        "planning_snapshot.json": planning,
        "planning_validation_report.json": planning_validation,
        "timetable.json": timetable,
        "gates.json": gates,
        "connection_audit.json": connection_audit,
    }
    for filename, value in artifacts.items():
        if filename in {"timetable.json", "gates.json"}:
            write_json(output / filename, value, indent=1, trailing_newline=False)
        else:
            write_json(output / filename, value)

    connection_decision = copy.deepcopy(config.get("connectionScopeDecision"))
    if (
        connection_decision is not None
        and connection_decision.get("status") != "approved"
    ):
        raise ValueError("Optimization release requires an approved scope decision")
    report = {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "status": "released",
        "sourceScheduleId": config["sourceScheduleId"],
        "overlayIds": [pin["id"] for pin in overlay_pins],
        "summary": actual,
        "validation": {
            "structural": structural["status"],
            "operating": operating["status"],
            "planningReconstruction": planning_validation["status"],
        },
        "connectionFinding": (
            f"All {connection_audit['summary']['directRoundTripCities']} target cities "
            f"have direct {config['connectionAudit']['hub']} round trips, but only "
            f"{connection_audit['summary']['connectedDirectionalPairs']}/"
            f"{connection_audit['summary']['directionalPairs']} directional cross-group "
            "pairs meet the configured connection window."
        ),
        "connectionScopeDecision": connection_decision,
        "patchScope": copy.deepcopy(config.get("patchScope")),
        "artifacts": sorted(artifacts),
    }
    write_json(output / "release_report.json", report)
    return {**report, "outputDirectory": output}
