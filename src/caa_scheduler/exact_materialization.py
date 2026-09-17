from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from .bank_placement import _curfew_status, _maximum_spaced_departures
from .demand import load_demand_sources_from_manifest
from .routing import (
    _connection_wait,
    _cycles,
    _local_minute,
    _match_station_successors,
    _utc_minute,
)
from .routing_repair import _leg_inventory
from .spacing import pairing_spacing_rule


TIME_STEP_MINUTES = 5
AIRCRAFT_OBJECTIVE_WEIGHT = 1_000_000.0
MIP_RELATIVE_GAP = 0.01
MIP_TIME_LIMIT_SECONDS = 120
SPACING_EXCEPTION_OBJECTIVE_WEIGHT = 10_000.0


def blocked_exact_materialization_plan(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    planning_rules_id: str,
    message: str,
) -> dict[str, Any]:
    """Return a durable diagnostic when a bounded exact solve has no incumbent."""
    configured_aircraft = sum(
        int(value) for value in canonical["schedule"]["fleetCounts"].values()
    )
    planned_legs = int(frequency_plan["summary"]["plannedLegs"])
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "exact_time_expanded_materialization",
        "planningRulesId": planning_rules_id,
        "operatingPolicyId": canonical["operatingPolicy"]["id"],
        "status": "fail",
        "materializationStatus": "blocked",
        "timeStepMinutes": TIME_STEP_MINUTES,
        "summary": {
            "checks": 1,
            "passed": 0,
            "failed": 1,
            "plannedLegs": planned_legs,
            "routedLegs": 0,
            "bankTouchLegs": 0,
            "bankAlignedLegs": 0,
            "nonHubLegs": 0,
            "nonHubIntegratedLegs": 0,
            "configuredAircraft": configured_aircraft,
            "requiredAircraft": 0,
            "remainingAircraft": 0,
            "cycles": 0,
            "curfewViolations": 0,
            "destinationsWithoutRon": 0,
            "rollingRonViolations": 0,
            "successorSwaps": 0,
        },
        "checks": [
            {"id": "solver_completion", "status": "fail", "message": message}
        ],
        "fleetPlan": {},
        "ronAssignments": {},
        "solver": {
            "name": "scipy-highs-time-expanded-milp",
            "relativeGap": MIP_RELATIVE_GAP,
            "timeLimitSecondsPerFleet": MIP_TIME_LIMIT_SECONDS,
            "fleets": {},
        },
        "cycles": [],
        "legs": [],
        "diagnostics": {"solverFailure": message},
        "nextStep": {
            "status": "blocked",
            "action": "retry_exact_materialization",
            "message": (
                "Exact materialization did not produce a complete feasible incumbent; "
                "review the solver diagnostic and retry before assigning canonical identifiers."
            ),
        },
        "limitations": [
            "No canonical identifiers or publishable consumer exports may be generated from a blocked exact solve.",
            "A bounded solve can require more computation for a changed network or fleet configuration.",
        ],
    }


def _inside_windows(value: int, windows: list[dict[str, Any]]) -> bool:
    return any(
        int(window["startMinute"]) <= value < int(window["endMinute"])
        for window in windows
    )


def _bank_id(value: int, windows: list[dict[str, Any]]) -> str | None:
    return next(
        (
            str(window["id"])
            for window in windows
            if int(window["startMinute"]) <= value < int(window["endMinute"])
        ),
        None,
    )


def _circular_distance(first: int, second: int) -> int:
    return min((first - second) % 1440, (second - first) % 1440)


def _assign_destination_rons(
    repair_plan: dict[str, Any],
    destinations: set[str],
    fleet_counts: dict[str, int],
) -> dict[str, str]:
    eligible: defaultdict[str, set[str]] = defaultdict(set)
    for route in repair_plan["routes"]:
        station = str(route["ronStation"])
        if station in destinations:
            eligible[station].add(str(route["fleet"]))
    missing = sorted(destinations - set(eligible))
    if missing:
        raise ValueError(
            "Topology repair has no RON-capable fleet for: " + ", ".join(missing)
        )

    assigned_counts: defaultdict[str, int] = defaultdict(int)
    assignments = {}
    for destination in sorted(destinations, key=lambda item: (len(eligible[item]), item)):
        fleet = min(
            eligible[destination],
            key=lambda item: (
                assigned_counts[item] / int(fleet_counts[item]),
                assigned_counts[item],
                item,
            ),
        )
        assignments[destination] = fleet
        assigned_counts[fleet] += 1
    return assignments


def _timing_cost(
    origin: str,
    destination: str,
    departure_utc: int,
    arrival_utc: int,
    cities: dict[str, dict[str, Any]],
    targets: dict[str, dict[str, list[int]]],
) -> float:
    cost = departure_utc / 1440
    if origin in targets:
        departure_local = _local_minute(departure_utc, origin, cities)
        cost += min(
            _circular_distance(departure_local, target)
            for target in targets[origin]["departure"]
        )
    if destination in targets:
        arrival_local = _local_minute(arrival_utc, destination, cities)
        cost += min(
            _circular_distance(arrival_local, target)
            for target in targets[destination]["arrival"]
        )
    return float(cost)


def _solve_fleet(
    fleet: str,
    copies: list[dict[str, Any]],
    configured_aircraft: int,
    assigned_rons: list[str],
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    windows: dict[str, list[dict[str, Any]]],
    targets: dict[str, dict[str, list[int]]],
    pairing_departure_counts: Counter[tuple[str, str]],
    station_departure_counts: Counter[str],
    reserved_pair_departures: dict[tuple[str, str], list[int]],
    enforce_pairing_spacing: bool,
    allow_pairing_spacing_exceptions: bool,
    time_limit_seconds: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    grouped: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for leg in copies:
        grouped[
            (
                leg["origin"],
                leg["destination"],
                leg["classification"],
                int(leg["blockMinutes"]),
            )
        ].append(leg)
    group_items = sorted(grouped.items())

    y_rows: list[dict[str, Any]] = []
    y_by_type: defaultdict[int, list[int]] = defaultdict(list)
    arrivals: defaultdict[tuple[str, int], list[int]] = defaultdict(list)
    departures: defaultdict[tuple[str, int], list[int]] = defaultdict(list)
    pairing_departures: defaultdict[
        tuple[str, str], defaultdict[int, list[int]]
    ] = defaultdict(lambda: defaultdict(list))
    station_events: defaultdict[str, set[int]] = defaultdict(set)
    objective: list[float] = []
    upper_bounds: list[float] = []

    for type_index, (key, legs) in enumerate(group_items):
        origin, destination, classification, block = key
        for departure_utc in range(0, 1440, TIME_STEP_MINUTES):
            departure_local = _local_minute(departure_utc, origin, cities)
            arrival_utc = (departure_utc + block) % 1440
            arrival_local = _local_minute(arrival_utc, destination, cities)
            if origin in windows and not _inside_windows(
                departure_local, windows[origin]
            ):
                continue
            if destination in windows and not _inside_windows(
                arrival_local, windows[destination]
            ):
                continue
            if (
                _curfew_status(origin, departure_local, arrival_local, policy)
                != "pass"
            ):
                continue
            index = len(y_rows)
            ready_utc = (departure_utc + block + minimum_turn) % 1440
            y_rows.append(
                {
                    "type": type_index,
                    "origin": origin,
                    "destination": destination,
                    "classification": classification,
                    "blockMinutes": block,
                    "departureUtcMinute": departure_utc,
                    "arrivalUtcMinute": arrival_utc,
                    "readyUtcMinute": ready_utc,
                }
            )
            y_by_type[type_index].append(index)
            departures[(origin, departure_utc)].append(index)
            pairing_departures[(origin, destination)][departure_utc].append(index)
            arrivals[(destination, ready_utc)].append(index)
            station_events[origin].add(departure_utc)
            station_events[destination].add(ready_utc)
            objective.append(
                _timing_cost(
                    origin,
                    destination,
                    departure_utc,
                    arrival_utc,
                    cities,
                    targets,
                )
            )
            upper_bounds.append(float(len(legs)))
        if not y_by_type[type_index]:
            raise ValueError(
                f"No curfew-safe exact bank time exists for "
                f"{origin}-{destination}-{fleet}"
            )

    q_by_event: dict[tuple[str, int], int] = {}
    for station in sorted(station_events):
        for minute in sorted(station_events[station]):
            q_by_event[(station, minute)] = len(objective)
            objective.append(0.0)
            upper_bounds.append(float(configured_aircraft))

    rows: list[dict[int, float]] = []
    lower_bounds: list[float] = []
    row_upper_bounds: list[float] = []
    for type_index, (_, legs) in enumerate(group_items):
        rows.append({index: 1.0 for index in y_by_type[type_index]})
        lower_bounds.append(float(len(legs)))
        row_upper_bounds.append(float(len(legs)))

    spacing_constraints = 0
    spacing_reserved_rejections = 0
    spacing_exception_variables = 0
    spacing_policy_exception_capacity = 0
    if enforce_pairing_spacing:
        hubs = set(policy["hubs"])
        section26 = policy["section26"]
        for pairing, departures_by_minute in sorted(pairing_departures.items()):
            total_departures = int(pairing_departure_counts[pairing])
            if total_departures < 2:
                continue
            origin, destination = pairing
            rule = pairing_spacing_rule(
                origin,
                destination,
                total_departures,
                int(station_departure_counts[origin]),
                hubs,
                section26,
            )
            minimum_gap = float(rule["minimumGapMinutes"])
            hard_floor = float(rule["hardFloorMinutes"])
            reserved = reserved_pair_departures.get(pairing, [])
            for minute, indices in departures_by_minute.items():
                if any(
                    _circular_distance(minute, other) < hard_floor
                    for other in reserved
                ):
                    for index in indices:
                        if upper_bounds[index] != 0.0:
                            upper_bounds[index] = 0.0
                            spacing_reserved_rejections += 1

            seen_windows: set[tuple[int, ...]] = set()
            minutes = sorted(departures_by_minute)
            policy_exception_required = (
                allow_pairing_spacing_exceptions
                and int(rule["allowedExceptions"]) > 0
                and _maximum_spaced_departures(
                    set(minutes), int(np.ceil(minimum_gap))
                )
                < total_departures
            )
            constraint_gap = (
                hard_floor if policy_exception_required else minimum_gap
            )
            for anchor in minutes:
                indices = tuple(
                    sorted(
                        index
                        for minute in minutes
                        if (minute - anchor) % 1440 < constraint_gap
                        for index in departures_by_minute[minute]
                    )
                )
                if not indices or indices in seen_windows:
                    continue
                seen_windows.add(indices)
                rows.append({index: 1.0 for index in indices})
                lower_bounds.append(0.0)
                row_upper_bounds.append(1.0)
                spacing_constraints += 1

            if not policy_exception_required:
                continue

            allowed_exceptions = int(rule["allowedExceptions"])
            spacing_policy_exception_capacity += allowed_exceptions
            reserved_exception_pairs = sum(
                1
                for position, first in enumerate(reserved)
                for second in reserved[position + 1 :]
                if hard_floor
                <= _circular_distance(first, second)
                < minimum_gap
            )
            remaining_exceptions = allowed_exceptions - reserved_exception_pairs
            if remaining_exceptions < 0:
                raise ValueError(
                    f"Reserved {origin}-{destination} times already exceed the "
                    "Section 2.6 exception allowance"
                )

            exception_budget: dict[int, float] = {}
            for minute, indices in departures_by_minute.items():
                reserved_conflicts = sum(
                    1
                    for other in reserved
                    if hard_floor
                    <= _circular_distance(minute, other)
                    < minimum_gap
                )
                if reserved_conflicts:
                    for index in indices:
                        exception_budget[index] = (
                            exception_budget.get(index, 0.0)
                            + reserved_conflicts
                        )

            for position, first in enumerate(minutes):
                for second in minutes[position + 1 :]:
                    distance = _circular_distance(first, second)
                    if not hard_floor <= distance < minimum_gap:
                        continue
                    exception_index = len(objective)
                    objective.append(SPACING_EXCEPTION_OBJECTIVE_WEIGHT)
                    upper_bounds.append(1.0)
                    spacing_exception_variables += 1
                    row = {
                        index: 1.0
                        for index in (
                            departures_by_minute[first]
                            + departures_by_minute[second]
                        )
                    }
                    row[exception_index] = -1.0
                    rows.append(row)
                    lower_bounds.append(-np.inf)
                    row_upper_bounds.append(1.0)
                    spacing_constraints += 1
                    exception_budget[exception_index] = 1.0

            if exception_budget:
                rows.append(exception_budget)
                lower_bounds.append(0.0)
                row_upper_bounds.append(float(remaining_exceptions))
                spacing_constraints += 1

    for station in sorted(station_events):
        events = sorted(station_events[station])
        for position, minute in enumerate(events):
            previous = events[position - 1]
            row = {
                q_by_event[(station, minute)]: 1.0,
                q_by_event[(station, previous)]: -1.0,
            }
            for index in arrivals[(station, minute)]:
                row[index] = row.get(index, 0.0) - 1.0
            for index in departures[(station, minute)]:
                row[index] = row.get(index, 0.0) + 1.0
            rows.append(row)
            lower_bounds.append(0.0)
            row_upper_bounds.append(0.0)

    capacity_row: dict[int, float] = {}
    for station, events in station_events.items():
        reference_minute = 0 if 0 in events else max(events)
        capacity_row[q_by_event[(station, reference_minute)]] = 1.0
    for index, leg in enumerate(y_rows):
        unavailable_minutes = int(leg["blockMinutes"]) + minimum_turn
        departure_utc = int(leg["departureUtcMinute"])
        if departure_utc == 0 or departure_utc + unavailable_minutes > 1440:
            capacity_row[index] = capacity_row.get(index, 0.0) + 1.0
    rows.append(capacity_row)
    lower_bounds.append(0.0)
    row_upper_bounds.append(float(configured_aircraft))
    for index, coefficient in capacity_row.items():
        objective[index] += AIRCRAFT_OBJECTIVE_WEIGHT * coefficient

    for station in assigned_rons:
        boundary = _utc_minute(180, station, cities)
        events = sorted(station_events[station])
        state_minute = (
            boundary
            if boundary in station_events[station]
            else max(
                (minute for minute in events if minute < boundary),
                default=max(events),
            )
        )
        physical_presence = {q_by_event[(station, state_minute)]: 1.0}
        for index in departures[(station, boundary)]:
            physical_presence[index] = physical_presence.get(index, 0.0) + 1.0
        for index, leg in enumerate(y_rows):
            if leg["destination"] != station:
                continue
            if (boundary - int(leg["arrivalUtcMinute"])) % 1440 < minimum_turn:
                physical_presence[index] = (
                    physical_presence.get(index, 0.0) + 1.0
                )
        rows.append(physical_presence)
        lower_bounds.append(1.0)
        row_upper_bounds.append(np.inf)

    matrix_rows: list[int] = []
    matrix_columns: list[int] = []
    matrix_values: list[float] = []
    for row_index, row in enumerate(rows):
        for column_index, value in row.items():
            matrix_rows.append(row_index)
            matrix_columns.append(column_index)
            matrix_values.append(value)
    matrix = coo_matrix(
        (matrix_values, (matrix_rows, matrix_columns)),
        shape=(len(rows), len(objective)),
    ).tocsr()
    result = milp(
        c=np.asarray(objective),
        integrality=np.ones(len(objective)),
        bounds=Bounds(np.zeros(len(objective)), np.asarray(upper_bounds)),
        constraints=LinearConstraint(
            matrix,
            np.asarray(lower_bounds),
            np.asarray(row_upper_bounds),
        ),
        options={
            "time_limit": time_limit_seconds,
            "mip_rel_gap": MIP_RELATIVE_GAP,
        },
    )
    if result.x is None:
        raise ValueError(
            f"Exact {fleet} materialization failed: {result.message}"
        )
    maximum_fraction = max(abs(value - round(value)) for value in result.x)
    if maximum_fraction > 1e-6:
        raise ValueError(
            f"Exact {fleet} materialization returned fractional inventory"
        )

    materialized: dict[str, dict[str, Any]] = {}
    for type_index, (_, legs) in enumerate(group_items):
        selected_times = []
        for index in y_by_type[type_index]:
            selected_times.extend(
                [int(y_rows[index]["departureUtcMinute"])]
                * int(round(result.x[index]))
            )
        if len(selected_times) != len(legs):
            raise ValueError(
                f"Exact {fleet} materialization selected "
                f"{len(selected_times)} of {len(legs)} legs"
            )
        for leg, departure_utc in zip(
            sorted(legs, key=lambda row: row["id"]),
            sorted(selected_times),
        ):
            arrival_utc = departure_utc + int(leg["blockMinutes"])
            departure_local = _local_minute(
                departure_utc, leg["origin"], cities
            )
            arrival_local = _local_minute(
                arrival_utc, leg["destination"], cities
            )
            materialized[leg["id"]] = {
                **leg,
                "source": "exact_materialization",
                "departureUtcMinute": departure_utc,
                "arrivalUtcMinute": arrival_utc % 1440,
                "departureMinute": departure_local,
                "arrivalMinute": arrival_local,
                "originBankId": (
                    _bank_id(departure_local, windows[leg["origin"]])
                    if leg["origin"] in windows
                    else None
                ),
                "destinationBankId": (
                    _bank_id(arrival_local, windows[leg["destination"]])
                    if leg["destination"] in windows
                    else None
                ),
                "curfewStatus": "pass",
            }

    aircraft_required = round(
        sum(result.x[index] * value for index, value in capacity_row.items())
    )
    return materialized, {
        "status": "optimal_within_gap" if result.success else "feasible_time_limit",
        "message": str(result.message),
        "mipGap": round(float(getattr(result, "mip_gap", 0.0) or 0.0), 9),
        "legTypes": len(group_items),
        "timeVariables": len(y_rows),
        "inventoryVariables": len(q_by_event),
        "constraints": len(rows),
        "aircraftRequiredAtReference": int(aircraft_required),
        "assignedDestinationRons": len(assigned_rons),
        **(
            {
                "section26SpacingConstraints": spacing_constraints,
                "section26ReservedTimeRejections": spacing_reserved_rejections,
                "section26ExceptionVariables": spacing_exception_variables,
                "section26PolicyExceptionCapacity": spacing_policy_exception_capacity,
            }
            if enforce_pairing_spacing
            else {}
        ),
    }


def _cycle_score(
    cycles: list[dict[str, Any]],
    required_destinations: set[str],
    fleet_counts: dict[str, int],
    rolling_limit: int,
) -> tuple[int, int, int, int, int, int]:
    ron_cities = {
        stop["station"]
        for cycle in cycles
        for stop in cycle["ronStops"]
    }
    missing = len(required_destinations - ron_cities)
    required_by_fleet = {
        fleet: sum(
            int(cycle["aircraftRequired"])
            for cycle in cycles
            if cycle["fleet"] == fleet
        )
        for fleet in fleet_counts
    }
    shortfall = sum(
        max(0, required_by_fleet[fleet] - int(fleet_counts[fleet]))
        for fleet in fleet_counts
    )
    failures = [
        cycle
        for cycle in cycles
        if int(cycle["maximumDaysWithoutTargetRon"]) > rolling_limit
    ]
    return (
        missing,
        shortfall,
        len(failures),
        sum(
            int(cycle["maximumDaysWithoutTargetRon"]) - rolling_limit
            for cycle in failures
        ),
        max(
            (
                int(cycle["maximumDaysWithoutTargetRon"])
                for cycle in failures
            ),
            default=0,
        ),
        sum(required_by_fleet.values()),
    )


def _repair_successor_cycles(
    legs: dict[str, dict[str, Any]],
    successors: dict[str, str],
    policy: dict[str, Any],
    cities: dict[str, dict[str, Any]],
    required_destinations: set[str],
    fleet_counts: dict[str, int],
    rolling_limit: int,
    single_target_full_gap: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cycles = _cycles(
        legs,
        successors,
        policy,
        cities,
        single_target_full_gap=single_target_full_gap,
    )
    swaps = []
    arrivals_by_station: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for identifier, leg in legs.items():
        arrivals_by_station[(leg["fleet"], leg["destination"])].append(identifier)
    for identifiers in arrivals_by_station.values():
        identifiers.sort()

    for _ in range(20):
        current_score = _cycle_score(
            cycles, required_destinations, fleet_counts, rolling_limit
        )
        if current_score[:4] == (0, 0, 0, 0):
            break
        bad_legs = {
            leg_id
            for cycle in cycles
            if int(cycle["maximumDaysWithoutTargetRon"]) > rolling_limit
            for leg_id in cycle["legIds"]
        }
        best = None
        for arrivals in arrivals_by_station.values():
            for first_index, first in enumerate(arrivals):
                for second in arrivals[first_index + 1 :]:
                    if first not in bad_legs and second not in bad_legs:
                        continue
                    successors[first], successors[second] = (
                        successors[second],
                        successors[first],
                    )
                    candidate_cycles = _cycles(
                        legs,
                        successors,
                        policy,
                        cities,
                        single_target_full_gap=single_target_full_gap,
                    )
                    candidate_score = _cycle_score(
                        candidate_cycles,
                        required_destinations,
                        fleet_counts,
                        rolling_limit,
                    )
                    successors[first], successors[second] = (
                        successors[second],
                        successors[first],
                    )
                    if candidate_score >= current_score:
                        continue
                    if best is None or candidate_score < best[0]:
                        best = (
                            candidate_score,
                            first,
                            second,
                            candidate_cycles,
                        )
        if best is None:
            break
        score, first, second, candidate_cycles = best
        successors[first], successors[second] = (
            successors[second],
            successors[first],
        )
        swaps.append(
            {
                "firstArrivingLegId": first,
                "secondArrivingLegId": second,
                "beforeScore": list(current_score),
                "afterScore": list(score),
            }
        )
        cycles = candidate_cycles
    return cycles, swaps


def build_exact_materialization_plan(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    repair_plan: dict[str, Any],
    planning_rules: dict[str, Any],
) -> dict[str, Any]:
    if any(
        artifact.get("status") != "pass"
        for artifact in (frequency_plan, bank_plan, repair_plan)
    ):
        raise ValueError(
            "Exact materialization requires passing frequency, bank, and repair plans"
        )
    cities = {
        city["code"]: city for city in canonical["cities"] if city.get("active")
    }
    policy = canonical["operatingPolicy"]
    fleet_counts = canonical["schedule"]["fleetCounts"]
    profiles = {
        row["fleet"]: row
        for row in planning_rules["frequencyAllocation"]["fleetProfiles"]
    }
    inventory = _leg_inventory(frequency_plan, profiles, cities)
    unsupported = sorted(set(inventory) - set(fleet_counts))
    if unsupported:
        raise ValueError(
            "Exact materialization uses unconfigured fleets: "
            + ", ".join(unsupported)
        )
    windows = {
        row["hub"]: row["banks"]
        for row in bank_plan["hubs"]
    }
    targets = {
        row["hub"]: {
            "arrival": [
                int(bank["arrivalTargetMinute"]) for bank in row["banks"]
            ],
            "departure": [
                int(bank["departureTargetMinute"]) for bank in row["banks"]
            ],
        }
        for row in bank_plan["hubs"]
    }
    exemptions = set(policy.get("destinationRonExemptions", []))
    required_destinations = {
        city["code"]
        for city in cities.values()
        if city["role"] == "destination" and city["code"] not in exemptions
    }
    ron_assignments = _assign_destination_rons(
        repair_plan, required_destinations, fleet_counts
    )
    exact_options = planning_rules.get("exactMaterialization", {})
    spacing_options = exact_options.get("pairingSpacing", {})
    enforce_pairing_spacing = (
        spacing_options.get("mode")
        in {
            "section26_conservative_no_exception",
            "section26_policy_exception",
        }
    )
    allow_pairing_spacing_exceptions = (
        spacing_options.get("mode") == "section26_policy_exception"
    )
    time_limit_seconds = int(
        exact_options.get(
            "timeLimitSecondsPerFleet", MIP_TIME_LIMIT_SECONDS
        )
    )
    all_inventory_legs = [
        leg for fleet_legs in inventory.values() for leg in fleet_legs
    ]
    pairing_departure_counts = Counter(
        (str(leg["origin"]), str(leg["destination"]))
        for leg in all_inventory_legs
    )
    station_departure_counts = Counter(
        str(leg["origin"]) for leg in all_inventory_legs
    )
    reserved_pair_departures: defaultdict[
        tuple[str, str], list[int]
    ] = defaultdict(list)
    assigned_by_fleet: defaultdict[str, list[str]] = defaultdict(list)
    for destination, fleet in ron_assignments.items():
        assigned_by_fleet[fleet].append(destination)

    materialized: dict[str, dict[str, Any]] = {}
    solver_fleets = {}
    for fleet in fleet_counts:
        fleet_legs, solver = _solve_fleet(
            fleet,
            inventory.get(fleet, []),
            int(fleet_counts[fleet]),
            sorted(assigned_by_fleet[fleet]),
            cities,
            policy,
            windows,
            targets,
            pairing_departure_counts,
            station_departure_counts,
            reserved_pair_departures,
            enforce_pairing_spacing,
            allow_pairing_spacing_exceptions,
            time_limit_seconds,
        )
        materialized.update(fleet_legs)
        solver_fleets[fleet] = solver
        for leg in fleet_legs.values():
            reserved_pair_departures[
                (str(leg["origin"]), str(leg["destination"]))
            ].append(int(leg["departureUtcMinute"]))

    minimum_turn = int(policy["turns"]["minimumMinutes"])
    successors, _ = _match_station_successors(materialized, minimum_turn)
    rolling_limit = int(planning_rules["routing"]["rollingRonWindowDays"]) + int(
        policy["rollingRonGraceDays"]
    )
    cycles, swaps = _repair_successor_cycles(
        materialized,
        successors,
        policy,
        cities,
        required_destinations,
        fleet_counts,
        rolling_limit,
        bool(
            planning_rules["routing"].get(
                "singleTargetUsesFullCycleGap", False
            )
        ),
    )

    hubs = set(policy["hubs"])
    legs = [materialized[identifier] for identifier in sorted(materialized)]
    bank_touch = [
        leg
        for leg in legs
        if leg["origin"] in hubs or leg["destination"] in hubs
    ]
    nonhub = [
        leg
        for leg in legs
        if leg["origin"] not in hubs and leg["destination"] not in hubs
    ]
    bank_unaligned = [
        leg["id"]
        for leg in bank_touch
        if (leg["origin"] in hubs and leg["originBankId"] is None)
        or (
            leg["destination"] in hubs
            and leg["destinationBankId"] is None
        )
    ]
    curfew_violations = [
        leg["id"]
        for leg in legs
        if _curfew_status(
            leg["origin"],
            int(leg["departureMinute"]),
            int(leg["arrivalMinute"]),
            policy,
        )
        != "pass"
    ]
    continuity_violations = [
        [identifier, successor]
        for identifier, successor in successors.items()
        if materialized[identifier]["destination"]
        != materialized[successor]["origin"]
        or materialized[identifier]["fleet"]
        != materialized[successor]["fleet"]
    ]
    turn_violations = []
    for identifier, successor in successors.items():
        leg = materialized[identifier]
        following = materialized[successor]
        arrival_utc = int(leg["departureUtcMinute"]) + int(
            leg["blockMinutes"]
        )
        wait = _connection_wait(
            arrival_utc,
            int(following["departureUtcMinute"]),
            minimum_turn,
        )
        if wait < minimum_turn:
            turn_violations.append([identifier, successor, wait])

    ron_cities = {
        stop["station"]
        for cycle in cycles
        for stop in cycle["ronStops"]
    }
    missing_rons = sorted(required_destinations - ron_cities)
    rolling_violations = [
        cycle["id"]
        for cycle in cycles
        if int(cycle["maximumDaysWithoutTargetRon"]) > rolling_limit
    ]
    spacing_violations = []
    spacing_exceptions = []
    if enforce_pairing_spacing:
        hubs = set(policy["hubs"])
        section26 = policy["section26"]
        pair_departures: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
        for leg in legs:
            pair_departures[(leg["origin"], leg["destination"])].append(
                int(leg["departureMinute"]) % 1440
            )
        for pairing, departures in sorted(pair_departures.items()):
            if len(departures) < 2:
                continue
            origin, destination = pairing
            rule = pairing_spacing_rule(
                origin,
                destination,
                len(departures),
                int(station_departure_counts[origin]),
                hubs,
                section26,
            )
            ordered = sorted(departures)
            gaps = [
                (ordered[(index + 1) % len(ordered)] - minute) % 1440
                for index, minute in enumerate(ordered)
            ]
            hard_gaps = [gap for gap in gaps if gap < rule["hardFloorMinutes"]]
            short_gaps = [gap for gap in gaps if gap < rule["minimumGapMinutes"]]
            allowed_exceptions = (
                int(rule["allowedExceptions"])
                if allow_pairing_spacing_exceptions
                else 0
            )
            if hard_gaps or len(short_gaps) > allowed_exceptions:
                spacing_violations.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "departures": ordered,
                        "gaps": gaps,
                        "minimumGapMinutes": rule["minimumGapMinutes"],
                        "allowedExceptions": allowed_exceptions,
                    }
                )
            elif short_gaps:
                spacing_exceptions.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "departures": ordered,
                        "shortGaps": short_gaps,
                        "minimumGapMinutes": rule["minimumGapMinutes"],
                    }
                )
    fleet_plan = {}
    for fleet, configured in fleet_counts.items():
        fleet_cycles = [cycle for cycle in cycles if cycle["fleet"] == fleet]
        required = sum(int(cycle["aircraftRequired"]) for cycle in fleet_cycles)
        fleet_plan[fleet] = {
            "configuredAircraft": int(configured),
            "requiredAircraft": required,
            "shortfall": max(0, required - int(configured)),
            "remainingAircraft": max(0, int(configured) - required),
            "cycles": len(fleet_cycles),
            "routedLegs": sum(int(cycle["legCount"]) for cycle in fleet_cycles),
            "assignedDestinationRons": len(assigned_by_fleet[fleet]),
            "solverMipGap": solver_fleets[fleet]["mipGap"],
        }
    capacity_shortfall = sum(row["shortfall"] for row in fleet_plan.values())
    planned_legs = int(frequency_plan["summary"]["plannedLegs"])
    checks = [
        {
            "id": "service_coverage",
            "status": "pass" if len(legs) == planned_legs else "fail",
            "message": f"All {planned_legs} proposed legs receive exact times",
        },
        {
            "id": "nonhub_integration",
            "status": (
                "pass"
                if len(nonhub)
                == planned_legs - int(bank_plan["summary"]["hubMarketLegs"])
                else "fail"
            ),
            "message": f"All {len(nonhub)} non-hub legs are integrated into aircraft cycles",
        },
        {
            "id": "bank_core_alignment",
            "status": "pass" if not bank_unaligned else "fail",
            "message": (
                f"All {len(bank_touch)} hub-touching legs land inside approved bank cores"
                if not bank_unaligned
                else f"{len(bank_unaligned)} hub-touching legs miss their bank cores"
            ),
        },
        {
            "id": "routing_continuity",
            "status": "pass" if not continuity_violations else "fail",
            "message": (
                "Every exact successor retains station and fleet continuity"
                if not continuity_violations
                else f"{len(continuity_violations)} exact successors are discontinuous"
            ),
        },
        {
            "id": "minimum_turns",
            "status": "pass" if not turn_violations else "fail",
            "message": (
                f"Every exact connection meets the {minimum_turn}-minute floor"
                if not turn_violations
                else f"{len(turn_violations)} exact connections miss the turn floor"
            ),
        },
        {
            "id": "fleet_capacity",
            "status": "pass" if not capacity_shortfall else "fail",
            "message": (
                "Every exact cycle fits the fleet counts selected for this schedule"
                if not capacity_shortfall
                else f"Exact cycles require {capacity_shortfall} additional aircraft"
            ),
        },
        {
            "id": "curfew_enforcement",
            "status": "pass" if not curfew_violations else "fail",
            "hardStop": True,
            "message": (
                "Every exact leg is curfew compliant"
                if not curfew_violations
                else f"{len(curfew_violations)} exact legs violate a curfew"
            ),
        },
        {
            "id": "destination_ron_coverage",
            "status": "pass" if not missing_rons else "fail",
            "message": (
                f"All {len(required_destinations)} required destinations receive a real routed overnight"
                if not missing_rons
                else "Destinations without an exact routed overnight: "
                + ", ".join(missing_rons)
            ),
        },
        {
            "id": "rolling_target_ron",
            "status": "pass" if not rolling_violations else "fail",
            "message": (
                f"Every exact cycle reaches a target RON within {rolling_limit} days"
                if not rolling_violations
                else f"{len(rolling_violations)} exact cycles exceed the target-RON window"
            ),
        },
    ]
    if enforce_pairing_spacing:
        checks.append(
            {
                "id": "section_26_pairing_spacing",
                "status": "pass" if not spacing_violations else "fail",
                "message": (
                    (
                        f"Every exact directed pairing satisfies Section 2.6 spacing; {len(spacing_exceptions)} use the permitted one-gap exception"
                        if allow_pairing_spacing_exceptions
                        else "Every exact directed pairing clears the Section 2.6 spacing threshold without using its optional exception"
                    )
                    if not spacing_violations
                    else f"{len(spacing_violations)} exact directed pairings miss the Section 2.6 spacing threshold"
                ),
            }
        )
    failed = sum(check["status"] == "fail" for check in checks)
    required_aircraft = sum(
        int(row["requiredAircraft"]) for row in fleet_plan.values()
    )
    configured_aircraft = sum(int(value) for value in fleet_counts.values())
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "exact_time_expanded_materialization",
        "planningRulesId": planning_rules["id"],
        "operatingPolicyId": policy["id"],
        "status": "pass" if not failed else "fail",
        "materializationStatus": "complete" if not failed else "blocked",
        "timeStepMinutes": TIME_STEP_MINUTES,
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
            "plannedLegs": planned_legs,
            "routedLegs": len(legs),
            "bankTouchLegs": len(bank_touch),
            "bankAlignedLegs": len(bank_touch) - len(bank_unaligned),
            "nonHubLegs": len(nonhub),
            "nonHubIntegratedLegs": len(nonhub),
            "configuredAircraft": configured_aircraft,
            "requiredAircraft": required_aircraft,
            "remainingAircraft": configured_aircraft - required_aircraft,
            "cycles": len(cycles),
            "curfewViolations": len(curfew_violations),
            "destinationsWithoutRon": len(missing_rons),
            "rollingRonViolations": len(rolling_violations),
            "successorSwaps": len(swaps),
            **(
                {"spacingViolations": len(spacing_violations)}
                if enforce_pairing_spacing
                else {}
            ),
        },
        "checks": checks,
        "fleetPlan": fleet_plan,
        "ronAssignments": {
            destination: ron_assignments[destination]
            for destination in sorted(ron_assignments)
        },
        "solver": {
            "name": "scipy-highs-time-expanded-milp",
            "relativeGap": MIP_RELATIVE_GAP,
            "timeLimitSecondsPerFleet": time_limit_seconds,
            "fleets": solver_fleets,
            **(
                {
                    "pairingSpacingMode": spacing_options["mode"],
                    "pairingSpacingPolicyExceptionsUsed": len(spacing_exceptions),
                }
                if enforce_pairing_spacing
                else {}
            ),
        },
        "cycles": cycles,
        "legs": legs,
        "diagnostics": {
            "successorSwaps": swaps,
            "bankUnalignedLegs": bank_unaligned,
            "continuityViolations": continuity_violations,
            "turnViolations": turn_violations,
            "curfewViolations": curfew_violations,
            "missingDestinationRons": missing_rons,
            "rollingRonViolations": rolling_violations,
            **(
                {
                    "spacingViolations": spacing_violations,
                    "spacingExceptions": spacing_exceptions,
                }
                if enforce_pairing_spacing
                else {}
            ),
        },
        "nextStep": {
            "status": "ready" if not failed else "blocked",
            "action": "assign_canonical_identifiers" if not failed else "repair_exact_cycles",
            "message": (
                "Assign canonical Line/Day/Route, pairing, and flight identifiers, then run full operating and gate validation."
                if not failed
                else "Repair the remaining exact-cycle failures before assigning canonical identifiers."
            ),
        },
        "limitations": [
            "Exact materialization proves five-minute flight times, complete non-hub integration, aircraft-cycle continuity, fleet capacity, hard curfews, destination RONs, and rolling target-RON cadence.",
            "Gate and stand capacity has not yet been evaluated against these newly materialized cycles.",
            "Canonical Line/Day/Route, pairing, and flight identifiers remain unassigned until the next construction stage.",
        ],
    }


def build_exact_materialization_plan_from_manifest(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    repair_plan: dict[str, Any],
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loaded = load_demand_sources_from_manifest(manifest_path, repo_root)
    if loaded["manifest"]["id"] != frequency_plan["demandDataVersion"]:
        raise ValueError(
            "Frequency plan version does not match the exact materialization manifest"
        )
    if bank_plan["planningRulesId"] != loaded["planningRules"]["id"]:
        raise ValueError(
            "Bank plan version does not match the exact materialization manifest"
        )
    if repair_plan["planningRulesId"] != loaded["planningRules"]["id"]:
        raise ValueError(
            "Repair plan version does not match the exact materialization manifest"
        )
    return build_exact_materialization_plan(
        canonical,
        frequency_plan,
        bank_plan,
        repair_plan,
        loaded["planningRules"],
    )
