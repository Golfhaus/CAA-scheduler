from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable


def haversine_nm(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    radius_nm = 3440.065
    phi_1, phi_2 = math.radians(latitude_1), math.radians(latitude_2)
    delta_phi = math.radians(latitude_2 - latitude_1)
    delta_lambda = math.radians(longitude_2 - longitude_1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_nm * math.asin(math.sqrt(value))


def tier_hub_cap(percentile: float, tiers: Iterable[dict[str, Any]]) -> int:
    for tier in tiers:
        if percentile <= tier["maximumPercentile"]:
            return tier["maximumHubs"]
    raise ValueError("Multi-hub tier rules do not cover the supplied percentile")


def compute_multihub_assignments(
    cities: list[dict[str, Any]],
    intergroup_demand: list[dict[str, Any]],
    market_sizes: dict[str, float],
    rules: dict[str, Any],
) -> dict[str, Any]:
    """Pure replacement for the legacy path-bound multi-hub script."""
    hub_cities = sorted(
        (city for city in cities if city["role"] == "hub"),
        key=lambda city: (city.get("sourceOrder", math.inf), city["code"]),
    )
    hubs = [city["code"] for city in hub_cities]
    hub_source_rank = {hub: index for index, hub in enumerate(hubs)}
    coordinates = {
        city["code"]: (city.get("latitude"), city.get("longitude"))
        for city in cities
    }
    missing_hub_coordinates = [
        hub for hub in hubs if None in coordinates.get(hub, (None, None))
    ]
    if missing_hub_coordinates:
        raise ValueError(
            f"Hub coordinates are missing: {', '.join(missing_hub_coordinates)}"
        )

    group_points: defaultdict[str, list[tuple[float, float]]] = defaultdict(list)
    for city in cities:
        if city["role"] == "hub" or not city.get("group"):
            continue
        latitude, longitude = coordinates[city["code"]]
        if latitude is not None and longitude is not None:
            group_points[city["group"]].append((latitude, longitude))
    centroids = {
        group: (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        for group, points in group_points.items()
    }

    pair_data = {
        frozenset(record["groups"]): record for record in intergroup_demand
    }
    thresholds = rules["multiHubQualification"]["rankThresholds"]
    group_results = []
    qualified_by_group: dict[str, list[str]] = {}
    for group in sorted(centroids):
        servable = Counter({hub: 0.0 for hub in hubs})
        for other_group in sorted(centroids):
            if other_group == group:
                continue
            record = pair_data.get(frozenset((group, other_group)))
            if record is None:
                raise ValueError(
                    f"Intergroup demand is missing for {group}/{other_group}"
                )
            for hub in record["qualifiedHubs"]:
                if hub in servable:
                    servable[hub] += float(record["passengersPerDay"])
        ranked = sorted(
            hubs,
            key=lambda hub: (-servable[hub], hub_source_rank[hub]),
        )
        if not ranked:
            raise ValueError("At least one hub is required")
        primary = ranked[0]
        primary_distance = haversine_nm(
            *centroids[group], *coordinates[primary]
        )
        qualified = [primary]
        details = [
            {
                "hub": primary,
                "rank": "primary",
                "servablePassengersPerDay": servable[primary],
                "distanceRatio": 0.0,
                "qualified": True,
            }
        ]
        for threshold, hub in zip(thresholds, ranked[1:]):
            distance = haversine_nm(*centroids[group], *coordinates[hub])
            ratio = distance / primary_distance if primary_distance else math.inf
            qualifies = (
                servable[hub] >= threshold["minimumServablePassengersPerDay"]
                and ratio <= threshold["maximumDistanceRatio"]
            )
            details.append(
                {
                    "hub": hub,
                    "rank": threshold["rank"],
                    "servablePassengersPerDay": servable[hub],
                    "distanceRatio": ratio,
                    "qualified": qualifies,
                }
            )
            if not qualifies:
                break
            qualified.append(hub)
        qualified_by_group[group] = qualified
        group_results.append(
            {
                "group": group,
                "centroid": {
                    "latitude": centroids[group][0],
                    "longitude": centroids[group][1],
                },
                "qualifiedHubs": qualified,
                "rankings": details,
            }
        )

    non_hubs = [city for city in cities if city["role"] != "hub"]
    ordered = sorted(
        non_hubs,
        key=lambda city: (
            float(market_sizes.get(city["code"], 0)),
            city.get("sourceOrder", math.inf),
            city["code"],
        ),
    )
    percentiles = {
        city["code"]: ((index + 1) / len(ordered) * 100 if ordered else 0)
        for index, city in enumerate(ordered)
    }
    tiers = rules["multiHubQualification"]["cityPercentileHubCaps"]
    city_results = []
    for city in sorted(non_hubs, key=lambda item: item["code"]):
        group = city.get("group")
        if group not in qualified_by_group:
            raise ValueError(f"No multi-hub qualification is available for {city['code']}")
        percentile = percentiles[city["code"]]
        cap = tier_hub_cap(percentile, tiers)
        city_results.append(
            {
                "code": city["code"],
                "group": group,
                "marketSize": float(market_sizes.get(city["code"], 0)),
                "percentile": percentile,
                "maximumHubs": cap,
                "hubAssignments": qualified_by_group[group][:cap],
            }
        )
    return {"groups": group_results, "cities": city_results}


def reconstruct_planning_snapshot(
    canonical: dict[str, Any],
    *,
    demand_data_version: str | None = None,
) -> dict[str, Any]:
    """Reconstruct the durable plan represented by a canonical schedule.

    This replaces the migration-era fleet_routes.pkl and station_totals.json
    artifacts without pretending that final scheduled frequencies are raw demand.
    """
    legs = canonical["legs"]
    schedule = canonical["schedule"]
    market_counts = Counter(
        (leg["fleet"], leg["origin"], leg["destination"]) for leg in legs
    )
    station_totals = Counter(leg["origin"] for leg in legs)
    fleet_legs = Counter(leg["fleet"] for leg in legs)
    fleet_block_minutes = Counter()
    fleet_aircraft_days: defaultdict[str, set[tuple[str, int]]] = defaultdict(set)
    for leg in legs:
        fleet_block_minutes[leg["fleet"]] += (
            leg["arrivalMinute"] - leg["departureMinute"]
        )
        fleet_aircraft_days[leg["fleet"]].add((leg["line"], leg["day"]))

    minimum_turn = canonical["operatingPolicy"]["turns"]["minimumMinutes"]
    fleet_summary = {}
    for fleet, aircraft_count in schedule["fleetCounts"].items():
        leg_count = fleet_legs[fleet]
        aircraft_days_used = len(fleet_aircraft_days[fleet])
        turn_count = max(0, leg_count - aircraft_days_used)
        block_minutes = round(fleet_block_minutes[fleet], 3)
        minimum_turn_minutes = turn_count * minimum_turn
        fleet_summary[fleet] = {
            "aircraftCount": aircraft_count,
            "aircraftDaysUsed": aircraft_days_used,
            "legCount": leg_count,
            "blockMinutes": block_minutes,
            "minimumTurnMinutes": minimum_turn_minutes,
            "requiredAircraftMinutes": round(
                block_minutes + minimum_turn_minutes, 3
            ),
        }

    return {
        "schemaVersion": "1.0.0",
        "scheduleId": schedule["id"],
        "sourceKind": "canonical_reconstruction",
        "demandDataVersion": demand_data_version,
        "summary": {
            "legCount": len(legs),
            "marketRows": len(market_counts),
            "stationCount": len(station_totals),
            "fleetTypes": len(fleet_summary),
        },
        "fleetPlan": fleet_summary,
        "markets": [
            {
                "fleet": fleet,
                "origin": origin,
                "destination": destination,
                "legs": count,
            }
            for (fleet, origin, destination), count in sorted(market_counts.items())
        ],
        "stationTotals": dict(sorted(station_totals.items())),
        "hubAssignments": [
            {
                "code": city["code"],
                "hubs": list(city["hubAssignments"]),
            }
            for city in sorted(canonical["cities"], key=lambda item: item["code"])
            if city["role"] != "hub"
        ],
        "hubBankRequirements": dict(
            sorted(canonical["operatingPolicy"]["hubBankCounts"].items())
        ),
        "limitations": [
            "Final scheduled frequencies are reconstructed from canonical legs; raw demand allocation is not available in the migration baseline.",
            "Hub assignments are preserved from canonical city metadata; recomputation requires pinned airport O-D and intergroup-demand inputs.",
            "Hub-bank counts are policy requirements; the legacy workbook does not contain bank windows or per-leg assignments.",
        ],
    }


def validate_planning_snapshot(
    snapshot: dict[str, Any], canonical: dict[str, Any]
) -> dict[str, Any]:
    checks = []

    def add(check_id: str, passed: bool, message: str) -> None:
        checks.append(
            {"id": check_id, "status": "pass" if passed else "fail", "message": message}
        )

    market_total = sum(row["legs"] for row in snapshot.get("markets", []))
    station_total = sum(snapshot.get("stationTotals", {}).values())
    expected = len(canonical["legs"])
    add(
        "market_leg_total",
        market_total == expected,
        f"Market plan accounts for {market_total}/{expected} canonical legs",
    )
    add(
        "station_departure_total",
        station_total == expected,
        f"Station totals account for {station_total}/{expected} canonical departures",
    )
    configured_fleets = set(canonical["schedule"]["fleetCounts"])
    planned_fleets = set(snapshot.get("fleetPlan", {}))
    add(
        "fleet_plan_coverage",
        planned_fleets == configured_fleets,
        "Planning fleet types exactly match the schedule-specific fleet configuration",
    )
    known_cities = {city["code"] for city in canonical["cities"]}
    unknown_markets = sorted(
        {
            code
            for row in snapshot.get("markets", [])
            for code in (row["origin"], row["destination"])
            if code not in known_cities
        }
    )
    add(
        "market_city_coverage",
        not unknown_markets,
        "Every planned market references known city metadata"
        if not unknown_markets
        else f"Unknown cities in market plan: {unknown_markets}",
    )
    failed = sum(check["status"] == "fail" for check in checks)
    return {
        "scheduleId": snapshot.get("scheduleId"),
        "status": "pass" if failed == 0 else "fail",
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
        },
        "checks": checks,
    }
