from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .demand import load_demand_sources_from_manifest, parse_airport_od_matrix
from .gate_export import _capacity
from .gates import TOUCH_ARRIVAL_MINUTES, TOUCH_DEPARTURE_MINUTES
from .planning import haversine_nm


Market = tuple[str, str]


def _market(origin: str, destination: str) -> Market:
    return tuple(sorted((origin, destination)))  # type: ignore[return-value]


def _percentile(values: list[float], percentile: float) -> float:
    """Return a deterministic linearly interpolated percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _optimize_service_assignments(
    assignments: dict[str, list[str]],
    assignment_rows: list[dict[str, Any]],
    active_cities: dict[str, dict[str, Any]],
    hub_codes: list[str],
    matrix_values: dict[str, dict[str, float]],
    rules: dict[str, Any] | None,
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Select capacity-aware hub endpoints within each city's tier cap.

    The demand qualification remains the starting point.  When enabled by a
    versioned policy, strong previously-unselected hub markets can compete for
    an available tier slot.  A primary hub can remain anchored while every
    other slot is ranked by local demand, network coverage, and the reviewed
    endpoint-balance weights.
    """
    if not rules or not rules.get("allowNewHubMarkets", False):
        return assignments, {
            "enabled": False,
            "newMarketDemandThreshold": None,
            "assignmentChanges": [],
        }

    row_by_code = {row["code"]: row for row in assignment_rows}
    possible_new_demands = []
    for code in assignments:
        for hub in hub_codes:
            if hub in assignments[code]:
                continue
            possible_new_demands.append(
                float(matrix_values[code][hub])
                + float(matrix_values[hub][code])
            )
    threshold = _percentile(
        possible_new_demands,
        float(rules.get("minimumNewMarketDemandPercentile", 100)),
    )
    endpoint_weights = {
        str(code): float(weight)
        for code, weight in rules.get(
            "serviceAssignmentEndpointWeights", {}
        ).items()
    }
    coverage = rules.get("northernToFloridaCoverage", {})
    coverage_groups = set(coverage.get("originGroups", []))
    coverage_hub = str(coverage.get("connectingHub", ""))
    coverage_multiplier = float(coverage.get("scoreMultiplier", 1.0))
    optimized: dict[str, list[str]] = {}
    changes = []
    for code in sorted(assignments):
        original = list(assignments[code])
        cap = int(row_by_code[code]["maximumHubs"])
        candidates = set(original)
        for hub in hub_codes:
            two_way = (
                float(matrix_values[code][hub])
                + float(matrix_values[hub][code])
            )
            if two_way >= threshold:
                candidates.add(hub)

        anchored = []
        if rules.get("preservePrimaryHub", True) and original:
            anchored.append(original[0])
        ranked = sorted(
            (endpoint for endpoint in candidates if endpoint not in anchored),
            key=lambda endpoint: (
                -(
                    math.sqrt(
                        float(matrix_values[code][endpoint])
                        + float(matrix_values[endpoint][code])
                    )
                    * endpoint_weights.get(endpoint, 1.0)
                    * (
                        coverage_multiplier
                        if active_cities[code].get("group") in coverage_groups
                        and endpoint == coverage_hub
                        else 1.0
                    )
                ),
                endpoint,
            ),
        )
        selected = (anchored + ranked)[:cap]
        optimized[code] = selected
        if selected != original:
            changes.append(
                {
                    "code": code,
                    "originalAssignments": original,
                    "optimizedAssignments": selected,
                    "added": sorted(set(selected) - set(original)),
                    "removed": sorted(set(original) - set(selected)),
                }
            )
    return optimized, {
        "enabled": True,
        "newMarketDemandThreshold": round(threshold, 6),
        "assignmentChanges": changes,
    }


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


def _reconcile_service_assignments(
    active_cities: dict[str, dict[str, Any]],
    assignment_rows: list[dict[str, Any]],
    existing_pairs: set[Market],
    planning_rules: dict[str, Any],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Apply the versioned network boundary before allocating frequencies.

    Earlier migration stages deliberately retained every historical market.  In
    strict mode, a non-hub city's qualified hubs are the complete service
    boundary, except that a documented focus-city market may occupy one of the
    city's tier slots.  A focus-city substitution replaces the lowest-ranked
    qualified hub; it never increases the tier cap.
    """
    qualified = {
        row["code"]: list(row["hubAssignments"])
        for row in assignment_rows
        if row["code"] in active_cities
    }
    network_rules = planning_rules.get("networkReconciliation")
    if not network_rules:
        return qualified, {
            "mode": "preserve_historical_markets",
            "cityDecisions": [],
            "removedHistoricalServiceMarkets": [],
        }

    if network_rules.get("mode") != "strict_tier_caps":
        raise ValueError(
            "Unsupported network-reconciliation mode: "
            + str(network_rules.get("mode"))
        )

    substitutions = network_rules.get("focusCitySubstitutions", [])
    if len(substitutions) > 1:
        raise ValueError("Only one focus-city substitution policy is supported")
    substitution = substitutions[0] if substitutions else None
    focus_code = substitution.get("code") if substitution else None
    eligible_groups = set(substitution.get("eligibleGroups", [])) if substitution else set()
    maximum_slots = int(substitution.get("maximumSlots", 0)) if substitution else 0
    if maximum_slots not in {0, 1}:
        raise ValueError("Focus-city substitution maximumSlots must be zero or one")
    if focus_code and active_cities.get(focus_code, {}).get("role") != "focus_city":
        raise ValueError(f"Configured focus-city substitution {focus_code} is not active")

    by_code = {row["code"]: row for row in assignment_rows}
    effective: dict[str, list[str]] = {}
    city_decisions = []
    for code in sorted(qualified):
        row = by_code[code]
        cap = int(row["maximumHubs"])
        assignments = list(qualified[code][:cap])
        substitution_used = False
        if (
            maximum_slots
            and focus_code
            and code != focus_code
            and active_cities[code].get("group") in eligible_groups
            and _market(code, focus_code) in existing_pairs
        ):
            assignments = assignments[: max(0, cap - 1)] + [focus_code]
            substitution_used = True
        effective[code] = assignments
        city_decisions.append(
            {
                "code": code,
                "group": active_cities[code].get("group"),
                "percentile": row["percentile"],
                "hubCountCap": cap,
                "qualifiedHubs": list(qualified[code]),
                "serviceAssignments": assignments,
                "focusCitySubstitutionUsed": substitution_used,
            }
        )

    retained_service_pairs = {
        _market(code, endpoint)
        for code, endpoints in effective.items()
        for endpoint in endpoints
    }
    service_codes = {
        code
        for code, city in active_cities.items()
        if city["role"] in {"hub", "focus_city"}
    }
    removed_rows = []
    for market in sorted(existing_pairs):
        origin, destination = market
        if origin not in service_codes and destination not in service_codes:
            continue
        if active_cities[origin]["role"] == active_cities[destination]["role"] == "hub":
            continue
        if market in retained_service_pairs:
            continue
        removed_rows.append(
            {
                "origin": origin,
                "destination": destination,
                "reason": "outside_effective_tier_service_assignments",
            }
        )

    return effective, {
        "mode": "strict_tier_caps",
        "focusCitySubstitution": copy.deepcopy(substitution),
        "cityDecisions": city_decisions,
        "removedHistoricalServiceMarkets": removed_rows,
    }


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
    productive_minutes: dict[str, int],
    assignment_mode: str = "largest_first",
) -> dict[str, Any]:
    units = [
        (market, ordinal)
        for market, frequency in frequencies.items()
        for ordinal in range(1, frequency + 1)
    ]
    units.sort(key=lambda row: (-demand[row[0]], row[0], row[1]))
    remaining = {
        profile["fleet"]: float(
            fleet_counts[profile["fleet"]]
            * productive_minutes[profile["fleet"]]
        )
        for profile in profiles
    }
    assignments: defaultdict[Market, Counter[str]] = defaultdict(Counter)
    work: Counter[str] = Counter()
    if assignment_mode == "demand_ranked_capacity_share":
        market_rows = sorted(
            (
                market
                for market, frequency in frequencies.items()
                if frequency > 0
            ),
            key=lambda market: (-demand[market], market),
        )
        reference_work = {
            market: frequencies[market]
            * sum(
                round_trip_costs[(market, profile["fleet"])]
                for profile in profiles
            )
            / len(profiles)
            for market in market_rows
        }
        total_reference_work = sum(reference_work.values())
        total_available = sum(
            fleet_counts[profile["fleet"]]
            * productive_minutes[profile["fleet"]]
            for profile in profiles
        )
        cumulative_targets = []
        cumulative = 0.0
        for profile in profiles:
            cumulative += (
                fleet_counts[profile["fleet"]]
                * productive_minutes[profile["fleet"]]
                / total_available
                if total_available
                else 0.0
            )
            cumulative_targets.append(cumulative * total_reference_work)

        consumed_reference = 0.0
        unassigned = []
        for market in market_rows:
            frequency = int(frequencies[market])
            midpoint = consumed_reference + reference_work[market] / 2
            target_index = next(
                (
                    index
                    for index, threshold in enumerate(cumulative_targets)
                    if midpoint <= threshold + 1e-9
                ),
                len(profiles) - 1,
            )
            candidate_indexes = sorted(
                range(len(profiles)),
                key=lambda index: (
                    abs(index - target_index),
                    index,
                ),
            )
            selected = next(
                (
                    profiles[index]["fleet"]
                    for index in candidate_indexes
                    if frequency
                    * round_trip_costs[
                        (market, profiles[index]["fleet"])
                    ]
                    <= remaining[profiles[index]["fleet"]] + 1e-9
                ),
                None,
            )
            if selected is None:
                unassigned.extend(
                    (market, ordinal)
                    for ordinal in range(1, frequency + 1)
                )
            else:
                required = frequency * round_trip_costs[(market, selected)]
                remaining[selected] -= required
                work[selected] += required
                assignments[market][selected] = frequency
            consumed_reference += reference_work[market]
        return {
            "assignments": assignments,
            "work": work,
            "remaining": remaining,
            "unassigned": unassigned,
        }
    if assignment_mode != "largest_first":
        raise ValueError(
            f"Unsupported fleet-assignment mode: {assignment_mode}"
        )

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


def _consolidate_market_fleets(
    allocation: dict[str, Any],
    profiles: list[dict[str, Any]],
    round_trip_costs: dict[tuple[Market, str], float],
) -> list[Market]:
    """Move every market onto one fleet when the routing policy requires it."""
    assignments: defaultdict[Market, Counter[str]] = allocation["assignments"]
    remaining: dict[str, float] = allocation["remaining"]
    work: Counter[str] = allocation["work"]
    fleet_order = [profile["fleet"] for profile in profiles]
    split_markets = sorted(
        market for market, rows in assignments.items() if len(rows) > 1
    )
    unconsolidated = []
    for market in split_markets:
        rows = assignments[market]
        total = sum(rows.values())
        existing = sorted(
            rows,
            key=lambda fleet: (-rows[fleet], fleet_order.index(fleet)),
        )
        candidates = existing + [
            fleet
            for fleet in reversed(fleet_order)
            if fleet not in rows
        ]
        target = next(
            (
                fleet
                for fleet in candidates
                if (
                    total * round_trip_costs[(market, fleet)]
                    - rows.get(fleet, 0) * round_trip_costs[(market, fleet)]
                )
                <= remaining[fleet] + 1e-9
            ),
            None,
        )
        if target is None:
            unconsolidated.append(market)
            continue
        for fleet, count in list(rows.items()):
            if fleet == target:
                continue
            refunded = count * round_trip_costs[(market, fleet)]
            remaining[fleet] += refunded
            work[fleet] -= refunded
            del rows[fleet]
        current = rows.get(target, 0)
        added = (total - current) * round_trip_costs[(market, target)]
        remaining[target] -= added
        work[target] += added
        rows[target] = total
    return unconsolidated


def _rebalance_connecting_markets(
    allocation: dict[str, Any],
    classifications: dict[Market, str],
    demand: dict[Market, float],
    round_trip_costs: dict[tuple[Market, str], float],
    active_cities: dict[str, dict[str, Any]],
    runway_thresholds: dict[str, int],
    rules: dict[str, Any] | None,
) -> dict[str, Any]:
    """Promote high-demand connecting markets into exact-routing headroom."""
    if not rules:
        return {
            "sourceFleet": None,
            "targetFleet": None,
            "minimumRoundTrips": 0,
            "promotedRoundTrips": 0,
            "markets": [],
        }
    source = str(rules["sourceFleet"])
    target = str(rules["targetFleet"])
    minimum = int(rules["minimumPromotedRoundTrips"])
    maximum_market_round_trips = rules.get("maximumPromotedMarketRoundTrips")
    eligible_classifications = set(rules["eligibleClassifications"])
    assignments: defaultdict[Market, Counter[str]] = allocation["assignments"]
    remaining: dict[str, float] = allocation["remaining"]
    work: Counter[str] = allocation["work"]
    runway_floor = int(runway_thresholds[target])

    candidates = []
    for market, fleets in assignments.items():
        source_round_trips = int(fleets.get(source, 0))
        if (
            not source_round_trips
            or len(fleets) != 1
            or classifications[market] not in eligible_classifications
            or (
                maximum_market_round_trips is not None
                and source_round_trips > int(maximum_market_round_trips)
            )
        ):
            continue
        known_runways = [
            int(active_cities[code]["runwayLengthFeet"])
            for code in market
            if active_cities[code].get("runwayLengthFeet") is not None
        ]
        if known_runways and min(known_runways) < runway_floor:
            continue
        candidates.append(
            (
                -float(demand[market]),
                market,
                source_round_trips,
            )
        )

    promoted = 0
    rows = []
    for _, market, round_trips in sorted(candidates):
        if promoted >= minimum:
            break
        target_cost = round_trips * round_trip_costs[(market, target)]
        if target_cost > remaining[target] + 1e-9:
            continue
        source_cost = round_trips * round_trip_costs[(market, source)]
        del assignments[market][source]
        assignments[market][target] = round_trips
        remaining[source] += source_cost
        work[source] -= source_cost
        remaining[target] -= target_cost
        work[target] += target_cost
        promoted += round_trips
        rows.append(
            {
                "origin": market[0],
                "destination": market[1],
                "classification": classifications[market],
                "twoWayDemand": demand[market],
                "roundTrips": round_trips,
                "sourceFleet": source,
                "targetFleet": target,
                "runwayScreening": (
                    "passed_populated_lengths"
                    if any(
                        active_cities[code].get("runwayLengthFeet") is not None
                        for code in market
                    )
                    else "pending_missing_lengths"
                ),
            }
        )
    return {
        "sourceFleet": source,
        "targetFleet": target,
        "minimumRoundTrips": minimum,
        "promotedRoundTrips": promoted,
        "markets": rows,
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

    assigned_hubs, network_reconciliation = _reconcile_service_assignments(
        active_cities,
        assignment_rows,
        existing_pairs,
        planning_rules,
    )

    matrix_values = matrix["values"]
    assigned_hubs, optimization_audit = _optimize_service_assignments(
        assigned_hubs,
        assignment_rows,
        active_cities,
        hub_codes,
        matrix_values,
        planning_rules.get("networkOptimization"),
    )
    network_reconciliation["optimization"] = optimization_audit

    retained_existing_pairs = set(existing_pairs)
    if optimization_audit["enabled"]:
        selected_service_pairs = {
            _market(code, endpoint)
            for code, endpoints in assigned_hubs.items()
            for endpoint in endpoints
        }
        service_codes = {
            code
            for code, city in active_cities.items()
            if city["role"] in {"hub", "focus_city"}
        }
        removed_historical_pairs = {
            market
            for market in existing_pairs
            if bool(set(market) & service_codes)
            and not (
                active_cities[market[0]]["role"]
                == active_cities[market[1]]["role"]
                == "hub"
            )
            and market not in selected_service_pairs
        }
        network_reconciliation["removedHistoricalServiceMarkets"] = [
            {
                "origin": market[0],
                "destination": market[1],
                "reason": "outside_optimized_tier_service_assignments",
            }
            for market in sorted(removed_historical_pairs)
        ]
    else:
        removed_historical_pairs = {
            _market(row["origin"], row["destination"])
            for row in network_reconciliation["removedHistoricalServiceMarkets"]
        }
    for row in network_reconciliation["removedHistoricalServiceMarkets"]:
        market = _market(row["origin"], row["destination"])
        row["historicalLegs"] = historical_legs[market]
        row["historicalFleetLegs"] = dict(
            sorted(historical_fleets[market].items())
        )
    retained_existing_pairs -= removed_historical_pairs

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
    candidate_pairs = retained_existing_pairs | required_pairs | inter_hub_pairs
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

    network_optimization = planning_rules.get("networkOptimization")
    point_to_point_competes = bool(
        network_optimization
        and network_optimization.get(
            "competeRetainedPointToPointMarkets", False
        )
    )
    frequencies = {
        market: (
            0
            if point_to_point_competes
            and classifications[market] == "point_to_point"
            else 1
        )
        for market in candidate_pairs
    }
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
    default_productive_minutes = int(
        allocation_rules["productiveMinutesPerAircraftDay"]
    )
    configured_productive_minutes = allocation_rules.get(
        "productiveMinutesPerAircraftDayByFleet", {}
    )
    productive_minutes = {
        fleet: int(
            configured_productive_minutes.get(
                fleet, default_productive_minutes
            )
        )
        for fleet in fleet_counts
    }
    assignment_mode = str(
        allocation_rules.get("fleetAssignmentMode", "largest_first")
    )
    ceiling = int(allocation_rules["marketFrequencyCeilingRoundTrips"])
    interhub_ceiling = int(
        allocation_rules.get(
            "interHubMarketFrequencyCeilingRoundTrips", ceiling
        )
    )

    enforce_hub_gate_throughput = bool(
        allocation_rules.get("enforceHubGateBankThroughput", False)
    )
    hub_gate_capacity: dict[str, int] = {}
    if enforce_hub_gate_throughput:
        bank_counts = planning_rules["bankPlacement"].get(
            "hubBankCountsOverride",
            canonical["operatingPolicy"]["hubBankCounts"],
        )
        bank_width = int(canonical["operatingPolicy"]["hubBankWindowMinutes"])
        touch_window = max(TOUCH_ARRIVAL_MINUTES, TOUCH_DEPARTURE_MINUTES)
        turns_per_gate_per_bank = (bank_width - 1) // touch_window + 1
        hub_gate_capacity = {
            hub: (
                _capacity(active_cities[hub])[0]
                * int(bank_counts[hub])
                * turns_per_gate_per_bank
            )
            for hub in hub_codes
        }

    def hub_gate_load(values: dict[Market, int], hub: str) -> int:
        return sum(frequency for market, frequency in values.items() if hub in market)

    def has_hub_gate_capacity(values: dict[Market, int], market: Market) -> bool:
        if not enforce_hub_gate_throughput:
            return True
        return all(
            hub_gate_load(values, hub) <= hub_gate_capacity[hub]
            for hub in market
            if hub in hub_gate_capacity
        )

    station_round_trip_capacity: dict[str, int] = {}
    station_score_capacity: dict[str, int] = {}
    if network_optimization:
        operating_minutes = int(
            network_optimization["stationOperatingMinutes"]
        )
        minutes_per_round_trip = int(
            network_optimization["stationGateMinutesPerRoundTrip"]
        )
        station_round_trip_capacity = {
            code: max(
                1,
                int(_capacity(city)[0] * operating_minutes / minutes_per_round_trip),
            )
            for code, city in active_cities.items()
        }
        station_score_capacity = dict(station_round_trip_capacity)
        station_round_trip_capacity.update(
            {
                str(code): int(capacity)
                for code, capacity in network_optimization.get(
                    "stationRoundTripCapacityOverrides", {}
                ).items()
            }
        )

    def station_load(values: dict[Market, int], station: str) -> int:
        return sum(
            frequency
            for market, frequency in values.items()
            if station in market
        )

    def has_station_capacity(values: dict[Market, int], market: Market) -> bool:
        if not station_round_trip_capacity:
            return True
        return all(
            station_load(values, station)
            <= station_round_trip_capacity[station]
            for station in market
        )

    endpoint_weights = {
        str(code): float(weight)
        for code, weight in (network_optimization or {}).get(
            "serviceAssignmentEndpointWeights", {}
        ).items()
    }
    coverage = (network_optimization or {}).get(
        "northernToFloridaCoverage", {}
    )
    coverage_groups = set(coverage.get("originGroups", []))
    coverage_hub = str(coverage.get("connectingHub", ""))
    coverage_multiplier = float(coverage.get("scoreMultiplier", 1.0))
    market_ceiling_overrides = {
        tuple(sorted(str(pair).split("-"))): int(value)
        for pair, value in (network_optimization or {}).get(
            "marketFrequencyCeilingRoundTripsOverrides", {}
        ).items()
    }

    def marginal_score(market: Market, next_frequency: int) -> float:
        endpoint_factor = math.prod(
            endpoint_weights.get(endpoint, 1.0)
            for endpoint in market
            if endpoint in endpoint_weights
        )
        spoke = next(
            (
                endpoint
                for endpoint in market
                if active_cities[endpoint]["role"] not in {"hub", "focus_city"}
            ),
            None,
        )
        network_factor = (
            coverage_multiplier
            if spoke is not None
            and active_cities[spoke].get("group") in coverage_groups
            and coverage_hub in market
            else 1.0
        )
        classification_factor = {
            "assigned_hub": 1.2,
            "supplemental_hub": 1.0,
            "focus_city": 1.1,
            "inter_hub": 1.15,
            "point_to_point": 0.85,
        }[classifications[market]]
        capacity_factor = math.prod(
            max(
                0.2,
                (
                    station_score_capacity[endpoint]
                    - station_load(frequencies, endpoint)
                )
                / station_score_capacity[endpoint],
            )
            for endpoint in market
        ) if station_round_trip_capacity else 1.0
        return (
            math.sqrt(max(0.0, demand[market]))
            * endpoint_factor
            * network_factor
            * classification_factor
            * capacity_factor
            / max(1, next_frequency)
        )

    def optional_score(market: Market, next_frequency: int) -> float:
        if network_optimization:
            return marginal_score(market, next_frequency)
        return math.sqrt(demand[market]) / max(1, next_frequency)

    def market_ceiling(market: Market) -> int:
        result = (
            interhub_ceiling
            if classifications[market] == "inter_hub"
            else ceiling
        )
        if (
            network_optimization
            and "BHM" in market
            and classifications[market] == "focus_city"
        ):
            result = min(
                result,
                int(
                    network_optimization[
                        "focusCityOptionalRoundTripCapPerMarket"
                    ]
                )
                + mandatory_frequencies.get(market, 0),
            )
        result = min(result, market_ceiling_overrides.get(market, result))
        if (
            point_to_point_competes
            and classifications[market] == "point_to_point"
        ):
            result = min(result, 1)
        return result

    def point_to_point_share_with(values: dict[Market, int]) -> float:
        total = sum(values.values())
        if not total:
            return 0.0
        return (
            sum(
                frequency
                for market, frequency in values.items()
                if classifications[market] == "point_to_point"
            )
            / total
        )

    capacity_removed_point_to_point_round_trips: list[Market] = []
    for market in candidate_pairs:
        applicable_ceiling = market_ceiling(market)
        if frequencies[market] <= applicable_ceiling:
            continue
        if classifications[market] != "point_to_point":
            raise ValueError(
                "A market-specific frequency ceiling cannot remove required "
                f"hub service: {'-'.join(market)}"
            )
        removed = frequencies[market] - applicable_ceiling
        frequencies[market] = applicable_ceiling
        mandatory_frequencies[market] = min(
            mandatory_frequencies[market], applicable_ceiling
        )
        capacity_removed_point_to_point_round_trips.extend(
            [market] * removed
        )

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
        assignment_mode,
    )

    if not allocation["unassigned"]:
        blocked: set[Market] = set()
        maximum_planned_legs = allocation_rules.get("maximumPlannedLegs")
        maximum_round_trips = (
            max(
                0,
                int(maximum_planned_legs) // 2
                - int(allocation_rules.get("routingReserveRoundTrips", 0)),
            )
            if maximum_planned_legs is not None
            else None
        )
        optional_score_floor = 0.0
        if network_optimization:
            initial_optional_scores = [
                marginal_score(market, frequencies[market] + 1)
                for market in candidate_pairs
                if (
                    classifications[market] != "point_to_point"
                    or point_to_point_competes
                )
                and frequencies[market] < market_ceiling(market)
            ]
            optional_score_floor = _percentile(
                initial_optional_scores,
                float(
                    network_optimization[
                        "minimumOptionalScorePercentile"
                    ]
                ),
            )
        while True:
            if (
                maximum_round_trips is not None
                and sum(frequencies.values()) >= maximum_round_trips
            ):
                break
            eligible = [
                market
                for market in candidate_pairs
                if market not in blocked
                and frequencies[market] < market_ceiling(market)
                and (
                    classifications[market] != "point_to_point"
                    or point_to_point_competes
                )
            ]
            eligible.sort(
                key=lambda market: (
                    -optional_score(market, frequencies[market] + 1),
                    market,
                )
            )
            if (
                network_optimization
                and eligible
                and optional_score(
                    eligible[0], frequencies[eligible[0]] + 1
                )
                < optional_score_floor
            ):
                break
            accepted = False
            for market in eligible:
                frequencies[market] += 1
                if (
                    classifications[market] == "point_to_point"
                    and point_to_point_share_with(frequencies)
                    > float(allocation_rules["pointToPointMaximumShare"])
                    + 1e-9
                ):
                    frequencies[market] -= 1
                    continue
                if not has_hub_gate_capacity(
                    frequencies, market
                ) or not has_station_capacity(frequencies, market):
                    frequencies[market] -= 1
                    blocked.add(market)
                    continue
                trial = _assign_frequencies(
                    frequencies,
                    demand,
                    profiles,
                    fleet_counts,
                    round_trip_costs,
                    productive_minutes,
                    assignment_mode,
                )
                if not trial["unassigned"]:
                    allocation = trial
                    accepted = True
                    break
                frequencies[market] -= 1
                blocked.add(market)
            if not accepted:
                break

    removed_point_to_point_round_trips: list[Market] = list(
        capacity_removed_point_to_point_round_trips
    )
    if network_optimization and not allocation["unassigned"]:
        point_to_point_limit = float(
            allocation_rules["pointToPointMaximumShare"]
        )
        while True:
            total_round_trips = sum(frequencies.values())
            point_to_point_round_trips = sum(
                frequencies[market]
                for market in candidate_pairs
                if classifications[market] == "point_to_point"
            )
            share = (
                point_to_point_round_trips / total_round_trips
                if total_round_trips
                else 0.0
            )
            if share <= point_to_point_limit + 1e-9:
                break
            removable = sorted(
                (
                    market
                    for market in candidate_pairs
                    if classifications[market] == "point_to_point"
                    and frequencies[market] > 0
                ),
                key=lambda market: (demand[market], market),
            )
            if not removable:
                break
            market = removable[0]
            frequencies[market] -= 1
            removed_point_to_point_round_trips.append(market)
            allocation = _assign_frequencies(
                frequencies,
                demand,
                profiles,
                fleet_counts,
                round_trip_costs,
                productive_minutes,
                assignment_mode,
            )

    assigned_counts: defaultdict[Market, Counter[str]] = allocation["assignments"]
    unconsolidated_markets = (
        _consolidate_market_fleets(allocation, profiles, round_trip_costs)
        if allocation_rules.get("requireSingleFleetPerMarket", False)
        else []
    )
    fleet_rebalancing_rules = allocation_rules.get("exactFleetRebalancing")
    if fleet_rebalancing_rules:
        target_fleet = str(fleet_rebalancing_rules["targetFleet"])
        target_minutes = int(
            fleet_rebalancing_rules["targetProductiveMinutesPerAircraftDay"]
        )
        if target_minutes < productive_minutes[target_fleet]:
            raise ValueError(
                "Exact fleet-rebalancing headroom cannot reduce productive minutes"
            )
        allocation["remaining"][target_fleet] += (
            target_minutes - productive_minutes[target_fleet]
        ) * int(fleet_counts[target_fleet])
        productive_minutes[target_fleet] = target_minutes
    fleet_rebalancing = _rebalance_connecting_markets(
        allocation,
        classifications,
        demand,
        round_trip_costs,
        active_cities,
        canonical["operatingPolicy"]["runwayScreeningFeet"],
        fleet_rebalancing_rules,
    )
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
    if network_optimization:
        network_reconciliation["optimization"][
            "removedPointToPointRoundTrips"
        ] = ["-".join(market) for market in removed_point_to_point_round_trips]
        if point_to_point_competes:
            network_reconciliation["optimization"][
                "omittedPointToPointMarkets"
            ] = [
                "-".join(market)
                for market in sorted(candidate_pairs)
                if classifications[market] == "point_to_point"
                and planned_frequency[market] == 0
            ]

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
                **(
                    {
                        "hubCountCap": row["maximumHubs"],
                        "qualifiedHubs": list(row["hubAssignments"]),
                        "serviceAssignments": list(hubs),
                        "focusCitySubstitutionUsed": "BHM" in hubs,
                    }
                    if network_reconciliation["mode"] == "strict_tier_caps"
                    else {}
                ),
                "minimumFlightLegs": minimum_legs,
                "plannedHubFlightLegs": planned_hub_legs,
                "plannedFlightLegs": planned_total_legs,
                "hubRoundTrips": hub_round_trips,
                "meetsMinimum": planned_hub_legs >= minimum_legs,
            }
        )

    fleet_plan = {}
    for fleet, aircraft_count in fleet_counts.items():
        available = aircraft_count * productive_minutes[fleet]
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
            **(
                {"productiveMinutesPerAircraftDay": productive_minutes[fleet]}
                if configured_productive_minutes
                else {}
            ),
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
                **(
                    {
                        "marginalSelectionScore": round(
                            marginal_score(
                                market,
                                max(1, planned_frequency[market]),
                            ),
                            6,
                        ),
                        "newOptimizedMarket": (
                            market in required_pairs
                            and market not in existing_pairs
                        ),
                    }
                    if network_optimization
                    else {}
                ),
                **(
                    {"frequencyCeilingRoundTrips": market_ceiling(market)}
                    if "interHubMarketFrequencyCeilingRoundTrips"
                    in allocation_rules
                    else {}
                ),
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
    hub_gate_rows = [
        {
            "hub": hub,
            "plannedRoundTrips": hub_gate_load(planned_frequency, hub),
            "maximumRoundTrips": capacity,
            "remainingRoundTrips": capacity
            - hub_gate_load(planned_frequency, hub),
        }
        for hub, capacity in sorted(hub_gate_capacity.items())
    ]
    station_capacity_rows = [
        {
            "station": station,
            "plannedRoundTrips": station_load(planned_frequency, station),
            "maximumRoundTrips": capacity,
            "remainingRoundTrips": capacity
            - station_load(planned_frequency, station),
        }
        for station, capacity in sorted(station_round_trip_capacity.items())
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
            "status": "pass"
            if all(
                value <= market_ceiling(market)
                for market, value in planned_frequency.items()
            )
            else "fail",
            "message": (
                f"Every market is at or below {ceiling} round trips"
                if "interHubMarketFrequencyCeilingRoundTrips"
                not in allocation_rules
                else (
                    "Every market is at or below its applicable ceiling "
                    f"({interhub_ceiling} inter-hub; {ceiling} otherwise)"
                )
            ),
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
    if allocation_rules.get("exactFleetRebalancing"):
        checks.append(
            {
                "id": "exact_fleet_rebalancing",
                "status": (
                    "pass"
                    if fleet_rebalancing["promotedRoundTrips"]
                    >= fleet_rebalancing["minimumRoundTrips"]
                    else "fail"
                ),
                "message": (
                    f"Promoted {fleet_rebalancing['promotedRoundTrips']} high-demand connecting round trips from "
                    f"{fleet_rebalancing['sourceFleet']} to {fleet_rebalancing['targetFleet']}"
                ),
            }
        )
    if allocation_rules.get("requireSingleFleetPerMarket", False):
        checks.append(
            {
                "id": "single_fleet_per_market",
                "status": "pass" if not unconsolidated_markets else "fail",
                "message": (
                    "Every market uses one fleet, so pairing-spacing slots are solved without cross-fleet reservations"
                    if not unconsolidated_markets
                    else "Markets split across fleets: "
                    + ", ".join("-".join(market) for market in unconsolidated_markets)
                ),
            }
        )
    if enforce_hub_gate_throughput:
        checks.append(
            {
                "id": "hub_gate_bank_throughput",
                "status": (
                    "pass"
                    if all(row["remainingRoundTrips"] >= 0 for row in hub_gate_rows)
                    else "fail"
                ),
                "message": (
                    "Every hub's planned frequency fits its gate-count, bank-count, and passenger-touch throughput"
                    if all(row["remainingRoundTrips"] >= 0 for row in hub_gate_rows)
                    else "One or more hubs exceed construction-time gate throughput"
                ),
            }
        )
    if network_optimization:
        station_capacity_passed = all(
            row["remainingRoundTrips"] >= 0
            for row in station_capacity_rows
        )
        checks.append(
            {
                "id": "station_gate_throughput",
                "status": "pass" if station_capacity_passed else "fail",
                "message": (
                    "Every station's planned frequency fits its gate-derived daily throughput envelope"
                    if station_capacity_passed
                    else "One or more stations exceed the gate-derived daily throughput envelope"
                ),
            }
        )
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
            **(
                {"mixedFleetMarkets": len(unconsolidated_markets)}
                if allocation_rules.get("requireSingleFleetPerMarket", False)
                else {}
            ),
            **(
                {
                    "fleetRebalancedMarkets": len(
                        fleet_rebalancing["markets"]
                    ),
                    "fleetRebalancedRoundTrips": fleet_rebalancing[
                        "promotedRoundTrips"
                    ],
                }
                if allocation_rules.get("exactFleetRebalancing")
                else {}
            ),
            **(
                {
                    "maximumPlannedLegs": allocation_rules.get(
                        "maximumPlannedLegs"
                    ),
                    **(
                        {
                            "routingReserveRoundTrips": int(
                                allocation_rules["routingReserveRoundTrips"]
                            ),
                            "effectivePlannedLegLimit": 2
                            * max(
                                0,
                                int(
                                    allocation_rules["maximumPlannedLegs"]
                                )
                                // 2
                                - int(
                                    allocation_rules[
                                        "routingReserveRoundTrips"
                                    ]
                                ),
                            ),
                        }
                        if allocation_rules.get("routingReserveRoundTrips")
                        else {}
                    ),
                    "removedHistoricalServiceMarkets": len(
                        removed_historical_pairs
                    ),
                    "focusCitySubstitutions": sum(
                        row.get("focusCitySubstitutionUsed", False)
                        for row in city_service
                    ),
                }
                if network_reconciliation["mode"] == "strict_tier_caps"
                else {}
            ),
        },
        "checks": checks,
        "fleetPlan": fleet_plan,
        "markets": market_rows,
        "cityService": city_service,
        **(
            {"fleetRebalancing": fleet_rebalancing}
            if allocation_rules.get("exactFleetRebalancing")
            else {}
        ),
        **({"hubGateCapacity": hub_gate_rows} if enforce_hub_gate_throughput else {}),
        **(
            {"stationGateCapacity": station_capacity_rows}
            if network_optimization
            else {}
        ),
        **(
            {"networkReconciliation": network_reconciliation}
            if network_reconciliation["mode"] == "strict_tier_caps"
            else {}
        ),
        "limitations": [
            (
                "Historical point-to-point markets remain eligible and compete for demand, network, fleet, and gate capacity; historical hub/focus markets outside each city's effective tier assignments are removed before allocation."
                if point_to_point_competes
                else "Historical point-to-point markets are retained, but historical hub/focus markets outside each city's effective tier assignments are removed before allocation."
                if network_reconciliation["mode"] == "strict_tier_caps"
                else "The existing canonical market set is retained as a seed; newly assigned hub markets are added, but entirely new point-to-point markets are not selected yet."
            ),
            (
                "Hub frequency is capped by the configured gates, effective bank count, bank width, and passenger-touch window; exact timing and physical gate/stand assignment remain mandatory downstream checks."
                if enforce_hub_gate_throughput
                else "Aircraft-minute allocation is a planning envelope, not a timed routing proof. Curfews, banks, gates, turns, RONs, and routing continuity remain mandatory downstream checks."
            ),
            (
                "Retained point-to-point markets compete for their first round trip and remain within the 10% schedule cap."
                if point_to_point_competes
                else "Optional point-to-point frequency is deliberately withheld; the preserved point-to-point market set must remain within the 10% schedule cap."
            ),
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
