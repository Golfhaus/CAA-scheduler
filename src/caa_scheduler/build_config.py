from __future__ import annotations

import re
from typing import Any


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
AIRPORT_PATTERN = re.compile(r"^[A-Z0-9]{3,4}$")
FLEET_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
VALID_MODES = {"mainline", "skunkworks"}
VALID_STARTING_POINTS = {"previous_schedule", "blank"}
VALID_NETWORK_ACTIONS = {"add", "remove", "status_change"}
VALID_CITY_STATUSES = {"destination", "focus_city", "hub", "inactive"}


def build_config_id(number: int, version: str) -> str:
    safe_version = re.sub(r"[^a-z0-9]+", "_", version.strip().lower()).strip("_")
    return f"schedule_{number}_v{safe_version or 'draft'}"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(
    check_id: str, title: str, passed: bool, message: str
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": "pass" if passed else "fail",
        "message": message,
    }


def validate_build_config(
    config: dict[str, Any], baseline: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate the portable build contract before schedule construction starts."""
    if not isinstance(config, dict):
        return {
            "buildId": None,
            "status": "fail",
            "summary": {"checks": 1, "passed": 0, "failed": 1},
            "checks": [
                _check(
                    "document",
                    "Configuration document",
                    False,
                    "Build configuration must be a JSON object",
                )
            ],
        }
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "schema_version",
            "Configuration schema",
            config.get("schemaVersion") == "1.0.0",
            "Build configuration schema version is 1.0.0"
            if config.get("schemaVersion") == "1.0.0"
            else "Build configuration schemaVersion must be 1.0.0",
        )
    )
    schedule = _mapping(config.get("schedule"))
    number = schedule.get("number")
    version = schedule.get("version")
    label = schedule.get("label")
    identity_valid = (
        isinstance(number, int)
        and not isinstance(number, bool)
        and number > 0
        and isinstance(version, str)
        and bool(version.strip())
        and isinstance(label, str)
        and bool(label.strip())
    )
    checks.append(
        _check(
            "schedule_identity",
            "Schedule identity",
            identity_valid,
            f"Schedule {number}, version {version}, is explicitly identified"
            if identity_valid
            else "Schedule number, version, and label are required",
        )
    )

    expected_build_id = (
        build_config_id(number, version) if identity_valid else None
    )
    checks.append(
        _check(
            "build_id",
            "Build identifier",
            expected_build_id is not None and config.get("buildId") == expected_build_id,
            f"Build identifier is {expected_build_id}"
            if expected_build_id is not None
            and config.get("buildId") == expected_build_id
            else "buildId must be derived from the schedule number and version",
        )
    )

    mode = schedule.get("mode")
    checks.append(
        _check(
            "build_mode",
            "Build mode",
            mode in VALID_MODES,
            f"{mode} promotion rules will apply"
            if mode in VALID_MODES
            else "Build mode must be mainline or skunkworks",
        )
    )

    starting_point = _mapping(config.get("startingPoint"))
    start_kind = starting_point.get("kind")
    schedule_id = starting_point.get("scheduleId")
    start_valid = start_kind in VALID_STARTING_POINTS and (
        (start_kind == "blank" and schedule_id is None)
        or (
            start_kind == "previous_schedule"
            and isinstance(schedule_id, str)
            and bool(schedule_id)
            and (
                baseline is None
                or schedule_id == baseline.get("schedule", {}).get("id")
            )
        )
    )
    checks.append(
        _check(
            "starting_point",
            "Starting point",
            start_valid,
            "The starting point is explicit and matches the loaded baseline"
            if start_valid
            else "Choose a blank start or the loaded published baseline",
        )
    )

    fleet_counts = config.get("fleetCounts")
    fleet_valid = (
        isinstance(fleet_counts, dict)
        and bool(fleet_counts)
        and all(
            isinstance(fleet, str)
            and FLEET_PATTERN.fullmatch(fleet) is not None
            and isinstance(count, int)
            and not isinstance(count, bool)
            and count >= 0
            for fleet, count in fleet_counts.items()
        )
    )
    checks.append(
        _check(
            "fleet_plan",
            "Schedule-specific fleet plan",
            fleet_valid,
            (
                f"{len(fleet_counts)} fleet types and "
                f"{sum(fleet_counts.values())} aircraft are explicitly recorded"
            )
            if fleet_valid
            else "At least one fleet type with a nonnegative whole-aircraft count is required",
        )
    )

    connection = _mapping(config.get("connectionWindowMinutes"))
    minimum = connection.get("minimum")
    maximum = connection.get("maximum")
    connection_valid = (
        isinstance(minimum, int)
        and not isinstance(minimum, bool)
        and isinstance(maximum, int)
        and not isinstance(maximum, bool)
        and 0 <= minimum < maximum
    )
    checks.append(
        _check(
            "connection_window",
            "Connection window",
            connection_valid,
            f"Connections are pinned to {minimum}-{maximum} minutes"
            if connection_valid
            else "Connection bounds must be whole minutes with maximum greater than minimum",
        )
    )

    inputs = _mapping(config.get("inputs"))
    instructions = _mapping(inputs.get("instructions"))
    city_source = _mapping(inputs.get("cityInformation"))
    policy_source = _mapping(inputs.get("operatingPolicy"))
    demand_source = _mapping(inputs.get("demandData"))
    input_pins_valid = (
        bool(instructions.get("version"))
        and bool(instructions.get("source"))
        and bool(city_source.get("filename"))
        and SHA256_PATTERN.fullmatch(str(city_source.get("sha256", ""))) is not None
        and bool(policy_source.get("filename"))
        and SHA256_PATTERN.fullmatch(str(policy_source.get("sha256", ""))) is not None
        and bool(demand_source.get("version"))
    )
    checks.append(
        _check(
            "input_pins",
            "Pinned build inputs",
            input_pins_valid,
            "Instructions, city information, operating policy, and demand data are pinned"
            if input_pins_valid
            else "Instruction, city, policy, and demand pins must all be complete",
        )
    )

    pin_consistency = True
    pin_message = "Pinned city and operating-policy inputs match the loaded baseline"
    if (
        baseline is not None
        and input_pins_valid
        and start_kind == "previous_schedule"
    ):
        provenance = baseline.get("provenance", {})
        for key, configured in (
            ("cityInformation", city_source),
            ("operatingPolicy", policy_source),
        ):
            pinned = provenance.get(key, {})
            if (
                configured.get("filename") != pinned.get("filename")
                or str(configured.get("sha256", "")).lower()
                != str(pinned.get("sha256", "")).lower()
            ):
                pin_consistency = False
                pin_message = (
                    "This compiler can only seed from a baseline whose city and policy "
                    "fingerprints match the build configuration"
                )
                break
    checks.append(
        _check(
            "baseline_pin_consistency",
            "Baseline input consistency",
            pin_consistency,
            pin_message,
        )
    )

    active_cities = {
        str(city.get("code", "")).upper(): bool(city.get("active"))
        for city in (baseline or {}).get("cities", [])
    }
    known_cities = set(active_cities)
    changes = config.get("networkChanges", [])
    network_errors: list[str] = []
    seen: set[str] = set()
    if not isinstance(changes, list):
        network_errors.append("networkChanges must be a list")
        changes = []
    for index, change in enumerate(changes, start=1):
        if not isinstance(change, dict):
            network_errors.append(f"row {index}: change must be an object")
            continue
        airport = str(change.get("airport", "")).upper()
        action = change.get("action")
        target = change.get("targetStatus", "")
        if AIRPORT_PATTERN.fullmatch(airport) is None:
            network_errors.append(f"row {index}: invalid airport code")
        if airport in seen:
            network_errors.append(f"{airport or f'row {index}'}: duplicate change")
        seen.add(airport)
        if action not in VALID_NETWORK_ACTIONS:
            network_errors.append(f"{airport or f'row {index}'}: invalid action")
        if action == "add" and active_cities.get(airport):
            network_errors.append(f"{airport}: already active")
        if action == "remove" and baseline is not None and not active_cities.get(airport):
            network_errors.append(f"{airport}: not an active baseline city")
        if (
            action == "status_change"
            and baseline is not None
            and airport not in known_cities
        ):
            network_errors.append(f"{airport}: not present in the baseline city roster")
        if action in {"add", "status_change"} and target not in VALID_CITY_STATUSES:
            network_errors.append(f"{airport}: target status is required")
    checks.append(
        _check(
            "network_changes",
            "Network changes",
            not network_errors,
            f"{len(changes)} proposed airport changes passed structural preflight"
            if not network_errors
            else "; ".join(network_errors),
        )
    )

    policy_pinned = input_pins_valid and pin_consistency
    checks.append(
        _check(
            "curfew_enforcement",
            "Curfew enforcement",
            policy_pinned,
            "The pinned operating policy will enforce curfew violations as hard stops"
            if policy_pinned
            else "Curfew enforcement cannot be guaranteed until the operating policy is pinned",
        )
    )

    failed = sum(item["status"] == "fail" for item in checks)
    return {
        "buildId": config.get("buildId"),
        "status": "pass" if failed == 0 else "fail",
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
        },
        "checks": checks,
    }
