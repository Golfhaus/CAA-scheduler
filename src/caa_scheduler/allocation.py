from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .demand import load_demand_sources_from_manifest, parse_airport_od_matrix
from .planning import haversine_nm


Market = tuple[str, str]


def _market(origin: str, destination: str) -> Market:
    return tuple(sorted((origin, destination)))  # type: ignore[return-value]


def _tier_minimum_flight_legs(
    percentile: float, tiers: list[dict[str, Any]]
) -> int:
    for tier in tiers:
        if percentile <= tier["maximumPercentile"]:
            return int(tier["minimumFlightLegs"])
    raise ValueError("Service-minimum tiers do not cover the supplied percentile")


def _market_classification(
    market: Market,
    roles: dict[str, str],
    assigned_hubs: dict[str, list[str]],
) -> str:
    origin, destination = market
    origin_role = roles[origin]
    destination_role = roles[destination]
    if origin_role == destination_role == "hub":
        return "inter_hub"
    if "hub" in {origin_role, destination_role}:
        hub = origin if origin_role == "hub" else destination
        other = destination if origin_role == "hub" else origin
        return (
            "assigned_hub"
            if hub in assigned_hubs.get(other, [])
            else "supplemental_hub"
        )
    if "focus_city" in {origin_role, destination_role}:
        return "focus_city"
    return "point_to_point"


def _round_trip_minutes(
    market: Market,
    fleet_profile: dict[str, Any],
    coordinates: dict[str, tuple[float, float]],
    turn_minutes: int,
) -> float:
    distance = haversine_nm(*coordinates[market[0]], *coordinates[market[1]])
    block = (
        float(fleet_profile["blockMinutesPerNauticalMile"]) * distance
        + float(fleet_profile["blockMinutesIntercept"])
    )
    return 2 * (block + turn_minutes)


def _assign_frequencies(
    frequencies: dict[Market, int],
    demand: dict[Market, float],
    profiles: list[dict[str, Any]],
    fleet_counts: dict[str, int],
    round_trip_costs: dict[tuple[Market, str], float],
    productive_minutes: int,
) -> dict[str, Any]:
    units = [
        (market, ordinal)
        for market, frequency in frequencies.items()
        for ordinal in range(1, frequency + 1)
    ]
    units.sort(key=lambda row: (-demand[row[0]], row[0], row[1]))
    remaining = {
        profile["fleet"]: float(fleet_counts[profile["fleet"]] * productive_minutes)
        for profile in profiles
    }
    assignments: defaultdict[Market, Counter[str]] = defaultdict(Counter)
    work: Counter[str] = Counter()
    unassigned = units
    for profile in profiles:
        fleet = profile["fleet"]
        still_unassigned = []
        for market, ordinal in unassigned:
            required = round_trip_costs[(market, fleet)]
            if required <= remaining[fleet] + 1e-9:
                remaining[fleet] -= required
                work[fleet] += required
                assignments[market][fleet] += 1
            else:
                still_unassigned.append((market, ordinal))
        unassigned = still_unassigned
    return {
        "assignments": assignments,
        "work": work,
        "remaining": remaining,
        "unassigned": unassigned,
    }


def build_frequency_fleet_plan(
    canonical: dict[str, Any],
    demand_plan: dict[str, Any],
    matrix: dict[str, Any],
    planning_rules: dict[str, Any],
) -> dict[str, Any]:
    """Allocate fresh frequencies and fleet work for an existing network seed.

    Aircraft quantities come only from ``canonical.schedule.fleetCounts``. The
    versioned planning rules describe supported fleet performance and the common
    aircraft-minute planning envelope, never the number of aircraft available.
    """
    if demand_plan.get("status") != "pass":
        raise ValueError("Frequency allocation requires a passing demand plan")

    allocation_rules = planning_rules["frequencyAllocation"]
    fleet_counts = canonical["schedule"]["fleetCounts"]
    profiles_by_fleet = {
        profile["fleet"]: profile
        for profile in allocation_rules["fleetProfiles"]
    }
    unsupported = sorted(
        fleet
        for fleet, count in fleet_counts.items()
        if count > 0 and fleet not in profiles_by_fleet
    )
    if unsupported:
        raise ValueError(
            "Planning policy has no performance profile for configured fleet types: "
            + ", ".join(unsupported)
        )
    profiles = sorted(
        (
            profiles_by_fleet[fleet]
            for fleet, count in fleet_counts.items()
            if count > 0
        ),
        key=lambda profile: (-profile["sizeRank"], profile["fleet"]),
    )
    if not profiles:
        raise ValueError("At least one configured aircraft is required for allocation")

    active_cities = {
        city["code"]: city for city in canonical["cities"] if city.get("active")
    }
    coordinates: dict[str, tuple[float, float]] = {}
    for code, city in active_cities.items():
        if city.get("latitude") is None or city.get("longitude") is None:
            raise ValueError(f"Planning coordinates are missing for {code}")
        coordinates[code] = (float(city["latitude"]), float(city["longitude"]))
    roles = {code: city["role"] for code, city in active_cities.items()}
    hub_codes = sorted(code for code, role in roles.items() if role == "hub")

    assignment_rows = demand_plan["multiHubAssignments"]["cities"]
    assigned_hubs = {
        row["code"]: list(row["hubAssignments"])
        for row in assignment_rows
        if row["code"] in active_cities
    }
    demand_city = {
        row["code"]: row
        for row in assignment_rows
        if row["code"] in active_cities
    }

    existing_pairs: set[Market] = set()
    historical_legs: Counter[Market] = Counter()
    historical_fleets: defaultdict[Market, Counter[str]] = defaultdict(Counter)
    for leg in canonical["legs"]:
        if leg["origin"] not in active_cities or leg["destination"] not in active_cities:
            continue
        market = _market(leg["origin"], leg["destination"])
        existing_pairs.add(market)
        historical_legs[market] += 1
        historical_fleets[market][leg["fleet"]] += 1

    required_pairs = {
        _market(code, hub)
        for code, hubs in assigned_hubs.items()
        for hub in hubs
    }
    inter_hub_pairs = {
        _market(origin, destination)
        for index, origin in enumerate(hub_codes)
        for destination in hub_codes[index + 1 :]
    }
    candidate_pairs = existing_pairs | required_pairs | inter_hub_pairs
    matrix_values = matrix["values"]
    demand = {
        market: round(
            float(matrix_values[market[0]][market[1]])
            + float(matrix_values[market[1]][market[0]]),
            6,
        )
        for market in candidate_pairs
    }
    classifications = {
        market: _market_classification(market, roles, assigned_hubs)
        for market in candidate_pairs
    }

    frequencies = {market: 1 for market in candidate_pairs}
    service_tiers = allocation_rules["serviceMinimumFlightLegs"]
    for code, city_row in sorted(demand_city.items()):
        hub_markets = [_market(code, hub) for hub in assigned_hubs[code]]
        minimum_legs = _tier_minimum_flight_legs(
            float(city_row["percentile"]), service_tiers
        )
        required_round_trips = math.ceil(minimum_legs / 2)
        remaining = max(
            0,
            required_round_trips
            - sum(frequencies[market] for market in hub_markets),
        )
        while remaining:
            selected = max(
                hub_markets,
                key=lambda market: (
                    math.sqrt(demand[market]) / (frequencies[market] + 1),
                    market,
                ),
            )
            frequencies[selected] += 1
            remaining -= 1

    mandatory_frequencies = dict(frequencies)
    turn_minutes = int(canonical["operatingPolicy"]["turns"]["minimumMinutes"])
    productive_minutes = int(allocation_rules["productiveMinutesPerAircraftDay"])
    ceiling = int(allocation_rules["marketFrequencyCeilingRoundTrips"])
    round_trip_costs = {
        (market, profile["fleet"]): _round_trip_minutes(
            market, profile, coordinates, turn_minutes
        )
        for market in candidate_pairs
        for profile in profiles
    }
    allocation = _assign_frequencies(
        frequencies,
        demand,
        profiles,
        fleet_counts,
        round_trip_costs,
        productive_minutes,
    )

    if not allocation["unassigned"]:
        blocked: set[Market] = set()
        while True:
            eligible = [
                market
                for market in candidate_pairs
                if market not in blocked
                and frequencies[market] < ceiling
                and classifications[market] != "point_to_point"
            ]
            eligible.sort(
                key=lambda market: (
                    -math.sqrt(demand[market]) / (frequencies[market] + 1),
                    market,
                )
            )
            accepted = False
            for market in eligible:
                frequencies[market] += 1
                trial = _assign_frequencies(
                    frequencies,
                    demand,
                    profiles,
                    fleet_counts,
                    round_trip_costs,
                    productive_minutes,
                )
                if not trial["unassigned"]:
                    allocation = trial
                    accepted = True
                    break
                frequencies[market] -= 1
                blocked.add(market)
            if not accepted:
                break

    assigned_counts: defaultdict[Market, Counter[str]] = allocation["assignments"]
    planned_frequency = {
        market: sum(assigned_counts[market].values()) for market in candidate_pairs
    }
    point_to_point_legs = sum(
        2 * planned_frequency[market]
        for market in candidate_pairs
        if classifications[market] == "point_to_point"
    )
    planned_round_trips = sum(planned_frequency.values())
    planned_legs = 2 * planned_round_trips
    point_to_point_share = (
        point_to_point_legs / planned_legs if planned_legs else 0.0
    )

    city_service = []
    for code, row in sorted(demand_city.items()):
        hubs = assigned_hubs[code]
        hub_round_trips = {
            hub: planned_frequency[_market(code, hub)] for hub in hubs
        }
        minimum_legs = _tier_minimum_flight_legs(
            float(row["percentile"]), service_tiers
        )
        planned_hub_legs = 2 * sum(hub_round_trips.values())
        planned_total_legs = 2 * sum(
            frequency
            for market, frequency in planned_frequency.items()
            if code in market
        )
        city_service.append(
            {
                "code": code,
                "percentile": row["percentile"],
                "minimumFlightLegs": minimum_legs,
                "plannedHubFlightLegs": planned_hub_legs,
                "plannedFlightLegs": planned_total_legs,
                "hubRoundTrips": hub_round_trips,
                "meetsMinimum": planned_hub_legs >= minimum_legs,
            }
        )

    fleet_plan = {}
    for fleet, aircraft_count in fleet_counts.items():
        available = aircraft_count * productive_minutes
        planned = round(float(allocation["work"].get(fleet, 0.0)), 3)
        fleet_markets = {
            market
            for market, assignments in assigned_counts.items()
            if assignments.get(fleet, 0)
        }
        round_trips = sum(
            assignments.get(fleet, 0) for assignments in assigned_counts.values()
        )
        fleet_plan[fleet] = {
            "aircraftCount": aircraft_count,
            "availableAircraftMinutes": available,
            "plannedAircraftMinutes": planned,
            "remainingAircraftMinutes": round(available - planned, 3),
            "utilization": round(planned / available, 6) if available else 0.0,
            "marketCount": len(fleet_markets),
            "roundTrips": round_trips,
            "legCount": 2 * round_trips,
        }

    market_rows = []
    for market in sorted(candidate_pairs):
        allocations = []
        for profile in profiles:
            fleet = profile["fleet"]
            round_trips = assigned_counts[market].get(fleet, 0)
            if not round_trips:
                continue
            per_round_trip = round_trip_costs[(market, fleet)]
            allocations.append(
                {
                    "fleet": fleet,
                    "roundTrips": round_trips,
                    "legCount": 2 * round_trips,
                    "plannedAircraftMinutes": round(
                        per_round_trip * round_trips, 3
                    ),
                }
            )
        market_rows.append(
            {
                "origin": market[0],
                "destination": market[1],
                "classification": classifications[market],
                "twoWayDemand": demand[market],
                "existingMarket": market in existing_pairs,
                "requiredByHubPlan": market in required_pairs,
                "mandatoryRoundTrips": mandatory_frequencies[market],
                "plannedRoundTrips": planned_frequency[market],
                "plannedLegs": 2 * planned_frequency[market],
                "historicalLegs": historical_legs.get(market, 0),
                "historicalFleetLegs": dict(sorted(historical_fleets[market].items())),
                "allocations": allocations,
            }
        )

    unassigned_mandatory = len(allocation["unassigned"])
    required_hub_gaps = [
        f"{row['code']}-{hub}"
        for row in city_service
        for hub, frequency in row["hubRoundTrips"].items()
        if frequency < 1
    ]
    checks = [
        {
            "id": "mandatory_capacity",
            "status": "pass" if unassigned_mandatory == 0 else "fail",
            "message": (
                "Every mandatory round trip fits the schedule-specific fleet plan"
                if unassigned_mandatory == 0
                else f"{unassigned_mandatory} mandatory round trips do not fit available aircraft-minutes"
            ),
        },
        {
            "id": "tier_minimum_service",
            "status": "pass" if all(row["meetsMinimum"] for row in city_service) else "fail",
            "message": (
                "Every non-hub city meets its percentile-tier hub-service minimum"
                if all(row["meetsMinimum"] for row in city_service)
                else "One or more cities fall below their percentile-tier hub-service minimum"
            ),
        },
        {
            "id": "hub_assignment_service",
            "status": "pass" if not required_hub_gaps else "fail",
            "message": (
                "Every assigned hub receives at least one round trip"
                if not required_hub_gaps
                else "Missing assigned-hub round trips: " + ", ".join(required_hub_gaps)
            ),
        },
        {
            "id": "market_frequency_ceiling",
            "status": "pass" if all(value <= ceiling for value in planned_frequency.values()) else "fail",
            "message": f"Every market is at or below {ceiling} round trips",
        },
        {
            "id": "point_to_point_share",
            "status": "pass"
            if point_to_point_share <= float(allocation_rules["pointToPointMaximumShare"]) + 1e-9
            else "fail",
            "message": (
                f"Point-to-point flying is {point_to_point_share:.1%} of planned legs"
            ),
        },
        {
            "id": "fleet_aircraft_minutes",
            "status": "pass"
            if all(row["remainingAircraftMinutes"] >= -1e-6 for row in fleet_plan.values())
            else "fail",
            "message": "Every fleet remains within its schedule-specific aircraft-minute budget",
        },
    ]
    failed = sum(check["status"] == "fail" for check in checks)
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "fresh_demand_allocation",
        "demandDataVersion": demand_plan["demandDataVersion"],
        "planningRulesId": planning_rules["id"],
        "status": "pass" if failed == 0 else "fail",
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
            "candidateMarkets": len(candidate_pairs),
            "newRequiredHubMarkets": len(required_pairs - existing_pairs),
            "mandatoryRoundTrips": sum(mandatory_frequencies.values()),
            "unassignedMandatoryRoundTrips": unassigned_mandatory,
            "optionalRoundTrips": max(
                0, planned_round_trips - sum(mandatory_frequencies.values())
            ),
            "plannedRoundTrips": planned_round_trips,
            "plannedLegs": planned_legs,
            "pointToPointLegs": point_to_point_legs,
            "pointToPointShare": round(point_to_point_share, 6),
        },
        "checks": checks,
        "fleetPlan": fleet_plan,
        "markets": market_rows,
        "cityService": city_service,
        "limitations": [
            "The existing canonical market set is retained as a seed; newly assigned hub markets are added, but entirely new point-to-point markets are not selected yet.",
            "Aircraft-minute allocation is a planning envelope, not a timed routing proof. Curfews, banks, gates, turns, RONs, and routing continuity remain mandatory downstream checks.",
            "Optional point-to-point frequency is deliberately withheld; the preserved point-to-point market set must remain within the 10% schedule cap.",
        ],
    }


def build_frequency_fleet_plan_from_manifest(
    canonical: dict[str, Any],
    demand_plan: dict[str, Any],
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loaded = load_demand_sources_from_manifest(manifest_path, repo_root)
    if loaded["manifest"]["id"] != demand_plan["demandDataVersion"]:
        raise ValueError("Demand plan version does not match the allocation manifest")
    matrix = parse_airport_od_matrix(loaded["airportOdMatrixText"])
    return build_frequency_fleet_plan(
        canonical,
        demand_plan,
        matrix,
        loaded["planningRules"],
    )
