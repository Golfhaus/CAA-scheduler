from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def validate_schedule(canonical: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    cities = canonical.get("cities", [])
    legs = canonical.get("legs", [])

    _check(checks, "schema_version", canonical.get("schemaVersion") == "1.0.0", "Canonical schema version is 1.0.0")
    _check(checks, "has_legs", bool(legs), f"Schedule contains {len(legs)} legs")
    provenance = canonical.get("provenance", {})
    workbook = provenance.get("workbook")
    construction = provenance.get("construction")
    file_pins = [
        provenance.get("cityInformation"),
        provenance.get("operatingPolicy"),
    ]
    imported = isinstance(workbook, dict) and construction is None
    generated = (
        isinstance(construction, dict)
        and workbook is None
        and construction.get("sourceKind") == "deterministic_planner"
        and bool(construction.get("sourceScheduleId"))
        and all(
            isinstance(construction.get(key), dict)
            and len(str(construction[key].get("sha256", ""))) == 64
            for key in (
                "buildConfig",
                "demandData",
                "planningRules",
                "exactMaterialization",
            )
        )
    )
    provenance_valid = (
        imported or generated
    ) and all(
        isinstance(pin, dict) and len(str(pin.get("sha256", ""))) == 64
        for pin in file_pins
    )
    _check(
        checks,
        "canonical_provenance",
        provenance_valid,
        (
            "Canonical schedule has exclusive imported-workbook provenance"
            if imported and provenance_valid
            else (
                "Canonical schedule has exclusive deterministic-construction provenance"
                if generated and provenance_valid
                else "Canonical schedule must pin exactly one imported or generated source chain"
            )
        ),
    )
    policy = canonical.get("operatingPolicy")
    policy_source = canonical.get("provenance", {}).get("operatingPolicy", {})
    policy_pinned = (
        isinstance(policy, dict)
        and bool(policy.get("id"))
        and isinstance(policy_source.get("sha256"), str)
        and len(policy_source["sha256"]) == 64
    )
    _check(
        checks,
        "operating_policy_pinned",
        policy_pinned,
        f"Operating policy {policy.get('id')} is embedded and pinned"
        if policy_pinned
        else "Canonical schedule must embed a versioned operating policy with SHA-256 provenance",
    )

    fleet_counts = canonical.get("schedule", {}).get("fleetCounts", {})
    scheduled_fleets = {leg.get("fleet") for leg in legs}
    fleet_plan_valid = (
        isinstance(fleet_counts, dict)
        and bool(fleet_counts)
        and scheduled_fleets <= set(fleet_counts)
        and all(
            isinstance(count, int) and not isinstance(count, bool) and count >= 0
            for count in fleet_counts.values()
        )
    )
    _check(
        checks,
        "schedule_fleet_plan",
        fleet_plan_valid,
        "Fleet counts are pinned as a schedule-specific build input"
        if fleet_plan_valid
        else "Every scheduled fleet needs a nonnegative count in schedule.fleetCounts",
    )

    city_codes = [city.get("code") for city in cities]
    duplicate_cities = _duplicates(city_codes)
    _check(
        checks,
        "unique_city_codes",
        not duplicate_cities,
        "City codes are unique" if not duplicate_cities else f"Duplicate city codes: {duplicate_cities}",
    )

    served_codes = {
        code
        for leg in legs
        for code in (leg.get("origin"), leg.get("destination"))
    }
    missing_city_metadata = sorted(served_codes - set(city_codes))
    _check(
        checks,
        "city_metadata_coverage",
        not missing_city_metadata,
        "Every served city has metadata"
        if not missing_city_metadata
        else f"Missing city metadata: {missing_city_metadata}",
    )

    flight_numbers = [leg.get("flight") for leg in legs]
    duplicate_flights = _duplicates(flight_numbers)
    _check(
        checks,
        "unique_flight_numbers",
        not duplicate_flights,
        "Flight numbers are unique"
        if not duplicate_flights
        else f"Duplicate flight numbers: {duplicate_flights[:20]}",
    )

    leg_ids = [leg.get("id") for leg in legs]
    duplicate_leg_ids = _duplicates(leg_ids)
    _check(
        checks,
        "unique_leg_ids",
        not duplicate_leg_ids,
        "Leg identifiers are unique"
        if not duplicate_leg_ids
        else f"Duplicate leg identifiers: {duplicate_leg_ids[:20]}",
    )

    bad_times = [
        leg.get("id")
        for leg in legs
        if not TIME_PATTERN.fullmatch(str(leg.get("departure", "")))
        or not TIME_PATTERN.fullmatch(str(leg.get("arrival", "")))
    ]
    _check(
        checks,
        "time_format",
        not bad_times,
        "Every departure and arrival uses 24-hour HH:MM"
        if not bad_times
        else f"Invalid times on legs: {bad_times[:20]}",
    )

    bad_operational_times = [
        leg.get("id")
        for leg in legs
        if not isinstance(leg.get("departureMinute"), (int, float))
        or not isinstance(leg.get("arrivalMinute"), (int, float))
        or not 0 <= leg["departureMinute"] < 1440
        or not leg["departureMinute"] < leg["arrivalMinute"] < 2880
    ]
    _check(
        checks,
        "operational_times",
        not bad_operational_times,
        "Every leg has an ordered operational minute interval"
        if not bad_operational_times
        else f"Invalid operational times on legs: {bad_operational_times[:20]}",
    )

    source_orders = [city.get("sourceOrder") for city in cities]
    duplicate_source_orders = _duplicates(source_orders)
    valid_source_order = not duplicate_source_orders and all(
        isinstance(value, int) and value >= 0 for value in source_orders
    )
    _check(
        checks,
        "city_source_order",
        valid_source_order,
        "City source order is complete and unique"
        if valid_source_order
        else f"Invalid or duplicate city source positions: {duplicate_source_orders[:20]}",
    )

    route_attributes: defaultdict[int, set[tuple[Any, Any, Any]]] = defaultdict(set)
    route_legs: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for leg in legs:
        route_attributes[leg["route"]].add((leg["line"], leg["fleet"], leg["day"]))
        route_legs[leg["route"]].append(leg)
    inconsistent_routes = sorted(route for route, values in route_attributes.items() if len(values) != 1)
    _check(
        checks,
        "route_identity",
        not inconsistent_routes,
        "Each route maps to exactly one line, fleet, and day"
        if not inconsistent_routes
        else f"Routes with inconsistent identity: {inconsistent_routes}",
    )

    continuity_breaks: list[dict[str, Any]] = []
    sequence_breaks: list[int] = []
    for route, items in route_legs.items():
        ordered = sorted(items, key=lambda leg: leg["sequenceWithinRoute"])
        if [leg["sequenceWithinRoute"] for leg in ordered] != list(range(1, len(ordered) + 1)):
            sequence_breaks.append(route)
        for previous, current in zip(ordered, ordered[1:]):
            if previous["destination"] != current["origin"]:
                continuity_breaks.append(
                    {
                        "route": route,
                        "afterFlight": previous["flight"],
                        "expectedOrigin": previous["destination"],
                        "actualOrigin": current["origin"],
                    }
                )
    _check(
        checks,
        "route_sequence",
        not sequence_breaks,
        "Sequence numbers are contiguous within every route"
        if not sequence_breaks
        else f"Routes with sequence gaps: {sequence_breaks}",
    )
    _check(
        checks,
        "routing_continuity",
        not continuity_breaks,
        "Every route is geographically continuous"
        if not continuity_breaks
        else f"Routing breaks: {continuity_breaks[:20]}",
    )

    pairings: defaultdict[int, set[tuple[str, str]]] = defaultdict(set)
    for leg in legs:
        pairings[leg["pairing"]].add((leg["origin"], leg["destination"]))
    bad_pairings = sorted(pairing for pairing, markets in pairings.items() if len(markets) != 1)
    _check(
        checks,
        "pairing_integrity",
        not bad_pairings,
        "Each pairing maps to one directed market"
        if not bad_pairings
        else f"Pairings assigned to multiple markets: {bad_pairings[:20]}",
    )

    connection = canonical.get("schedule", {}).get("connectionWindowMinutes", {})
    minimum = connection.get("minimum")
    maximum = connection.get("maximum")
    valid_window = (
        isinstance(minimum, int)
        and isinstance(maximum, int)
        and 0 <= minimum <= maximum
    )
    _check(
        checks,
        "connection_window",
        valid_window,
        f"Connection window is {minimum}-{maximum} minutes"
        if valid_window
        else "Connection window must contain nonnegative integer bounds with minimum <= maximum",
    )

    forced_splits = canonical.get("gatePlan", {}).get("forcedStandSplits", {})
    unknown_gate_cities = sorted(set(forced_splits) - set(city_codes))
    _check(
        checks,
        "gate_plan_cities",
        not unknown_gate_cities,
        "Every forced stand split references a known city"
        if not unknown_gate_cities
        else f"Unknown gate-plan cities: {unknown_gate_cities}",
    )

    passed = sum(check["status"] == "pass" for check in checks)
    failed = len(checks) - passed
    return {
        "scheduleId": canonical.get("schedule", {}).get("id"),
        "status": "pass" if failed == 0 else "fail",
        "summary": {"checks": len(checks), "passed": passed, "failed": failed},
        "metrics": {
            "flights": len(legs),
            "cities": len(cities),
            "servedCities": len(served_codes),
            "routes": len(route_legs),
            "lines": len({leg.get("line") for leg in legs}),
        },
        "checks": checks,
    }


def _check(checks: list[dict[str, Any]], check_id: str, passed: bool, message: str) -> None:
    checks.append({"id": check_id, "status": "pass" if passed else "fail", "message": message})


def _duplicates(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates, key=str)
