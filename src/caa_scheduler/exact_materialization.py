from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from .bank_placement import _curfew_status, _maximum_spaced_departures
from .demand import load_demand_sources_from_manifest
from .gate_export import _capacity
from .gates import (
    TOUCH_ARRIVAL_MINUTES,
    TOUCH_DEPARTURE_MINUTES,
    GateCapacityError,
    GateClaim,
    assign_gates,
)
from .io import read_json, write_json
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
BANK_OVERFLOW_OBJECTIVE_WEIGHT = 1_000_000_000.0
SEED_DEVIATION_OBJECTIVE_WEIGHT = 1_000_000.0
EXACT_SEED_MODEL_VERSION = "1.0.0"
HUB_OPERATION_CLOSURE_MAX_OVERFLOW_ROWS = 2
SUCCESSOR_PLATEAU_RANDOM_SEED = 20_260_918
LOGGER = logging.getLogger(__name__)


class ExactSeedStageComplete(RuntimeError):
    """Signal a successful bounded seed-only invocation."""

    def __init__(self, completed_fleets: list[str]):
        self.completed_fleets = completed_fleets
        super().__init__(
            "Exact seed checkpoint completed fleets: "
            + ", ".join(completed_fleets)
        )


class ExactGlobalRepairIncomplete(RuntimeError):
    """Signal that an improved global incumbent still exceeds bank capacity."""

    def __init__(
        self,
        bank_overflow: dict[str, float],
        solver_message: str,
        physical_capacity_overflow: dict[str, float] | None = None,
        passenger_gate_overflow: dict[str, float] | None = None,
    ):
        self.bank_overflow = bank_overflow
        self.physical_capacity_overflow = physical_capacity_overflow or {}
        self.passenger_gate_overflow = passenger_gate_overflow or {}
        combined_overflow = {
            **{f"bank:{key}": value for key, value in bank_overflow.items()},
            **{
                f"airport:{key}": value
                for key, value in self.physical_capacity_overflow.items()
            },
            **{
                f"gate:{key}": value
                for key, value in self.passenger_gate_overflow.items()
            },
        }
        total_overflow = sum(combined_overflow.values())
        maximum_overflow = max(combined_overflow.values())
        largest_overflows = ", ".join(
            f"{key}={value:.0f}"
            for key, value in sorted(
                combined_overflow.items(),
                key=lambda item: (-item[1], item[0]),
            )[:8]
        )
        super().__init__(
            "Exact global repair checkpoint retained "
            f"{total_overflow:.3f} units of feasibility overflow "
            f"(maximum row overage {maximum_overflow:.3f}; "
            f"largest rows: {largest_overflows}) after: {solver_message}"
        )


def _exact_seed_fingerprint(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    repair_plan: dict[str, Any],
    planning_rules: dict[str, Any],
) -> str:
    """Fingerprint every input that can affect an independent fleet seed."""
    payload = json.dumps(
        {
            "seedModelVersion": EXACT_SEED_MODEL_VERSION,
            "canonical": canonical,
            "frequencyPlan": frequency_plan,
            "bankPlan": bank_plan,
            "repairPlan": repair_plan,
            "planningRules": planning_rules,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_exact_seed_checkpoint(
    path: Path,
    fingerprint: str,
    seed_order: list[str],
) -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, dict[str, Any]],
]:
    if not path.exists():
        return {}, {}
    checkpoint = read_json(path)
    if checkpoint.get("schemaVersion") != "1.0.0":
        raise ValueError(f"Unsupported exact seed checkpoint schema: {path}")
    if checkpoint.get("seedModelVersion") != EXACT_SEED_MODEL_VERSION:
        raise ValueError(f"Unsupported exact seed model checkpoint: {path}")
    if checkpoint.get("fingerprint") != fingerprint:
        raise ValueError(
            f"Exact seed checkpoint does not match the current build inputs: {path}"
        )
    if checkpoint.get("seedOrder") != seed_order:
        raise ValueError(
            f"Exact seed checkpoint fleet order does not match the current build: {path}"
        )
    materialized_by_fleet = checkpoint.get("materializedByFleet", {})
    solver_fleets = checkpoint.get("solverFleets", {})
    if not isinstance(materialized_by_fleet, dict) or not isinstance(
        solver_fleets, dict
    ):
        raise ValueError(f"Malformed exact seed checkpoint: {path}")
    completed = set(checkpoint.get("completedFleets", []))
    if completed != set(materialized_by_fleet) or completed != set(solver_fleets):
        raise ValueError(f"Incomplete exact seed checkpoint indexes: {path}")
    if not completed.issubset(seed_order):
        raise ValueError(f"Exact seed checkpoint contains unknown fleets: {path}")
    return materialized_by_fleet, solver_fleets


def _write_exact_seed_checkpoint(
    path: Path,
    fingerprint: str,
    seed_order: list[str],
    materialized_by_fleet: dict[str, dict[str, dict[str, Any]]],
    solver_fleets: dict[str, dict[str, Any]],
) -> None:
    completed = [fleet for fleet in seed_order if fleet in materialized_by_fleet]
    temporary = path.with_name(path.name + ".tmp")
    write_json(
        temporary,
        {
            "schemaVersion": "1.0.0",
            "seedModelVersion": EXACT_SEED_MODEL_VERSION,
            "fingerprint": fingerprint,
            "seedOrder": seed_order,
            "completedFleets": completed,
            "materializedByFleet": {
                fleet: materialized_by_fleet[fleet] for fleet in completed
            },
            "solverFleets": {fleet: solver_fleets[fleet] for fleet in completed},
        },
        indent=None,
    )
    temporary.replace(path)


def _milp_with_start(
    objective: np.ndarray,
    integrality: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    matrix: Any,
    row_lower: np.ndarray,
    row_upper: np.ndarray,
    mip_start: np.ndarray,
    time_limit_seconds: int,
) -> SimpleNamespace:
    """Run bundled HiGHS with a complete incumbent supplied as a MIP start."""
    from scipy.optimize._highspy._core import (  # type: ignore[attr-defined]
        HighsLp,
        HighsModelStatus,
        HighsSolution,
        HighsSparseMatrix,
        HighsVarType,
        MatrixFormat,
        _Highs,
    )

    column_matrix = matrix.tocsc()
    sparse_matrix = HighsSparseMatrix()
    sparse_matrix.num_col_ = int(column_matrix.shape[1])
    sparse_matrix.num_row_ = int(column_matrix.shape[0])
    sparse_matrix.format_ = MatrixFormat.kColwise
    sparse_matrix.start_ = column_matrix.indptr.astype(np.int32)
    sparse_matrix.index_ = column_matrix.indices.astype(np.int32)
    sparse_matrix.value_ = column_matrix.data.astype(np.float64)
    sparse_matrix.p_end_ = np.asarray([], dtype=np.int32)

    linear_program = HighsLp()
    linear_program.num_col_ = int(column_matrix.shape[1])
    linear_program.num_row_ = int(column_matrix.shape[0])
    linear_program.col_cost_ = objective.astype(np.float64)
    linear_program.col_lower_ = lower.astype(np.float64)
    linear_program.col_upper_ = upper.astype(np.float64)
    linear_program.row_lower_ = row_lower.astype(np.float64)
    linear_program.row_upper_ = row_upper.astype(np.float64)
    linear_program.integrality_ = [
        HighsVarType.kInteger if value else HighsVarType.kContinuous
        for value in integrality
    ]
    linear_program.a_matrix_ = sparse_matrix

    solver = _Highs()
    solver.setOptionValue("output_flag", False)
    solver.setOptionValue("time_limit", float(time_limit_seconds))
    solver.setOptionValue("mip_rel_gap", MIP_RELATIVE_GAP)
    solver.passModel(linear_program)
    solution = HighsSolution()
    solution.col_value = mip_start.astype(np.float64)
    solution.value_valid = True
    solver.setSolution(solution)
    solver.run()
    model_status = solver.getModelStatus()
    solved = solver.getSolution()
    info = solver.getInfo()
    return SimpleNamespace(
        x=(
            np.asarray(solved.col_value, dtype=np.float64)
            if solved.value_valid
            else None
        ),
        success=model_status == HighsModelStatus.kOptimal,
        message=solver.modelStatusToString(model_status),
        mip_gap=float(info.mip_gap),
    )


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


def _apply_assigned_bank_waves(
    inventory: dict[str, list[dict[str, Any]]],
    bank_plan: dict[str, Any],
) -> None:
    """Attach each planned hub touch to its specific capacity-checked wave."""
    inventory_groups: defaultdict[
        tuple[str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for fleet_legs in inventory.values():
        for leg in fleet_legs:
            inventory_groups[
                (str(leg["fleet"]), str(leg["origin"]), str(leg["destination"]))
            ].append(leg)

    placement_groups: defaultdict[
        tuple[str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for placement in bank_plan["placements"]:
        placement_groups[
            (
                str(placement["fleet"]),
                str(placement["origin"]),
                str(placement["destination"]),
            )
        ].append(placement)

    for key, placements in sorted(placement_groups.items()):
        legs = sorted(inventory_groups.get(key, []), key=lambda row: row["id"])
        placements = sorted(
            placements,
            key=lambda row: (int(row["roundTripOrdinal"]), str(row["id"])),
        )
        if len(legs) != len(placements):
            fleet, origin, destination = key
            raise ValueError(
                f"Assigned-bank inventory mismatch for {origin}-{destination}-{fleet}: "
                f"{len(legs)} exact copies, {len(placements)} bank placements"
            )
        for leg, placement in zip(legs, placements):
            for touch in placement["bankTouches"]:
                field = (
                    "originBankId"
                    if touch["operation"] == "departure"
                    else "destinationBankId"
                )
                if field in leg:
                    raise ValueError(
                        f"Exact inventory leg {leg['id']} has multiple {field} values"
                    )
                leg[field] = str(touch["bankId"])


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


def _pairing_patterns(
    candidates: list[dict[str, Any]],
    frequency: int,
    minimum_gap: float,
    hard_floor: float,
    allowed_exceptions: int,
    reserved: list[int],
    maximum_patterns: int,
    beam_width: int,
) -> list[dict[str, Any]]:
    """Build deterministic, spacing-valid departure patterns for one pairing.

    Repeated copies of the same directional market are interchangeable.  Encoding
    every copy as an integer count at every minute leaves the MILP with a large
    symmetric search tree.  A pattern compiles that symmetry away: one binary
    choice represents all departures for the directional market.
    """
    if frequency < 1:
        return []

    ordered = sorted(
        candidates,
        key=lambda row: (int(row["departureUtcMinute"]), float(row["cost"])),
    )
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
        return []

    usable: list[tuple[dict[str, Any], int]] = []
    for candidate in ordered:
        minute = int(candidate["departureUtcMinute"])
        distances = [_circular_distance(minute, other) for other in reserved]
        if any(distance < hard_floor for distance in distances):
            continue
        exception_count = sum(
            hard_floor <= distance < minimum_gap for distance in distances
        )
        if exception_count <= remaining_exceptions:
            usable.append((candidate, exception_count))

    if frequency == 1:
        return [
            {
                "events": (candidate,),
                "cost": float(candidate["cost"])
                + SPACING_EXCEPTION_OBJECTIVE_WEIGHT * exception_count,
                "spacingExceptions": exception_count,
            }
            for candidate, exception_count in usable
        ]

    states: list[tuple[tuple[int, ...], float, int]] = [
        ((index,), float(candidate["cost"]), exception_count)
        for index, (candidate, exception_count) in enumerate(usable)
    ]
    ideal_gap = 1440.0 / frequency
    for depth in range(2, frequency + 1):
        expanded: list[tuple[tuple[int, ...], float, int]] = []
        for indices, cost, exception_count in states:
            first_minute = int(
                usable[indices[0]][0]["departureUtcMinute"]
            )
            last_minute = int(
                usable[indices[-1]][0]["departureUtcMinute"]
            )
            target = first_minute + (depth - 1) * ideal_gap
            viable: list[tuple[float, float, int]] = []
            for candidate_index in range(indices[-1] + 1, len(usable)):
                candidate, reserved_exceptions = usable[candidate_index]
                minute = int(candidate["departureUtcMinute"])
                distances = [
                    _circular_distance(
                        minute,
                        int(usable[prior][0]["departureUtcMinute"]),
                    )
                    for prior in indices
                ]
                if any(distance < hard_floor for distance in distances):
                    continue
                added_exceptions = reserved_exceptions + sum(
                    hard_floor <= distance < minimum_gap
                    for distance in distances
                )
                if exception_count + added_exceptions > remaining_exceptions:
                    continue
                viable.append(
                    (
                        abs(minute - target),
                        float(candidate["cost"]),
                        candidate_index,
                    )
                )

            # Target-near choices preserve broad time-of-day coverage; cheap
            # choices retain the bank-core objective.  Their union keeps the
            # bounded pattern set useful to the downstream fleet-flow solve.
            selected_indices = []
            seen_indices: set[int] = set()
            for _, _, candidate_index in sorted(viable)[:8] + sorted(
                viable, key=lambda row: (row[1], row[0], row[2])
            )[:4]:
                if candidate_index not in seen_indices:
                    selected_indices.append(candidate_index)
                    seen_indices.add(candidate_index)
            for candidate_index in selected_indices:
                candidate, reserved_exceptions = usable[candidate_index]
                minute = int(candidate["departureUtcMinute"])
                added_exceptions = reserved_exceptions + sum(
                    hard_floor
                    <= _circular_distance(
                        minute,
                        int(usable[prior][0]["departureUtcMinute"]),
                    )
                    < minimum_gap
                    for prior in indices
                )
                expanded.append(
                    (
                        indices + (candidate_index,),
                        cost + float(candidate["cost"]),
                        exception_count + added_exceptions,
                    )
                )

        if len(expanded) > beam_width:
            expanded.sort(
                key=lambda row: (
                    row[1]
                    + SPACING_EXCEPTION_OBJECTIVE_WEIGHT * row[2],
                    tuple(
                        int(usable[index][0]["departureUtcMinute"])
                        for index in row[0]
                    ),
                )
            )
            broadly_timed: dict[tuple[int, int, int], tuple[tuple[int, ...], float, int]] = {}
            for state in expanded:
                minutes = [
                    int(usable[index][0]["departureUtcMinute"])
                    for index in state[0]
                ]
                signature = (
                    minutes[0] // 30,
                    minutes[-1] // 30,
                    sum(minutes) // (30 * len(minutes)),
                )
                broadly_timed.setdefault(signature, state)
            retained = expanded[: beam_width // 2]
            retained_ids = {state[0] for state in retained}
            for state in broadly_timed.values():
                if state[0] not in retained_ids:
                    retained.append(state)
                    retained_ids.add(state[0])
                if len(retained) >= beam_width:
                    break
            states = retained
        else:
            states = expanded
        if not states:
            return []

    patterns = [
        {
            "events": tuple(usable[index][0] for index in indices),
            "cost": cost
            + SPACING_EXCEPTION_OBJECTIVE_WEIGHT * exception_count,
            "spacingExceptions": exception_count,
        }
        for indices, cost, exception_count in states
    ]
    patterns.sort(
        key=lambda row: (
            float(row["cost"]),
            tuple(
                int(event["departureUtcMinute"])
                for event in row["events"]
            ),
        )
    )
    if len(patterns) <= maximum_patterns:
        return patterns

    retained = patterns[: maximum_patterns // 2]
    retained_times = {
        tuple(int(event["departureUtcMinute"]) for event in row["events"])
        for row in retained
    }
    signatures: set[tuple[int, int, int]] = set()
    for row in patterns:
        minutes = [int(event["departureUtcMinute"]) for event in row["events"]]
        signature = (
            minutes[0] // 30,
            minutes[-1] // 30,
            sum(minutes) // (30 * len(minutes)),
        )
        if signature in signatures:
            continue
        signatures.add(signature)
        times = tuple(minutes)
        if times in retained_times:
            continue
        retained.append(row)
        retained_times.add(times)
        if len(retained) >= maximum_patterns:
            break
    if len(retained) < maximum_patterns:
        for row in patterns:
            times = tuple(
                int(event["departureUtcMinute"])
                for event in row["events"]
            )
            if times in retained_times:
                continue
            retained.append(row)
            retained_times.add(times)
            if len(retained) >= maximum_patterns:
                break
    return retained


def _solve_fleet_with_pairing_patterns(
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
    bank_touch_limits: dict[tuple[str, str], int] | None,
    bank_touch_constraint: str | None,
    feasibility_only: bool,
    allow_pairing_spacing_exceptions: bool,
    time_limit_seconds: int,
    maximum_patterns: int,
    beam_width: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Solve one fleet with repeated pairings compiled into binary patterns."""
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    grouped: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for leg in copies:
        if leg.get("originBankId") is not None or leg.get("destinationBankId") is not None:
            raise ValueError(
                "Pairing-pattern materialization requires joint bank assignment"
            )
        grouped[
            (
                leg["origin"],
                leg["destination"],
                leg["classification"],
                int(leg["blockMinutes"]),
            )
        ].append(leg)
    group_items = sorted(grouped.items())
    pairings = [(str(key[0]), str(key[1])) for key, _ in group_items]
    if len(pairings) != len(set(pairings)):
        raise ValueError(
            f"Pairing-pattern {fleet} inventory has duplicate directional groups"
        )

    section26 = policy["section26"]
    hubs = set(policy["hubs"])
    choices: list[dict[str, Any]] = []
    choices_by_type: defaultdict[int, list[int]] = defaultdict(list)
    pattern_counts: dict[str, int] = {}
    spacing_exception_capacity = 0
    for type_index, (key, legs) in enumerate(group_items):
        pattern_started = time.monotonic()
        origin, destination, classification, block = key
        candidates = []
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
            candidates.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "classification": classification,
                    "blockMinutes": block,
                    "departureUtcMinute": departure_utc,
                    "arrivalUtcMinute": arrival_utc,
                    "readyUtcMinute": (
                        departure_utc + block + minimum_turn
                    )
                    % 1440,
                    "originBankId": (
                        _bank_id(departure_local, windows[origin])
                        if origin in windows
                        else None
                    ),
                    "destinationBankId": (
                        _bank_id(arrival_local, windows[destination])
                        if destination in windows
                        else None
                    ),
                    "cost": _timing_cost(
                        origin,
                        destination,
                        departure_utc,
                        arrival_utc,
                        cities,
                        targets,
                    ),
                }
            )
        rule = pairing_spacing_rule(
            origin,
            destination,
            int(pairing_departure_counts[(origin, destination)]),
            int(station_departure_counts[origin]),
            hubs,
            section26,
        )
        allowed_exceptions = (
            int(rule["allowedExceptions"])
            if allow_pairing_spacing_exceptions
            else 0
        )
        spacing_exception_capacity += allowed_exceptions
        patterns = _pairing_patterns(
            candidates,
            len(legs),
            float(rule["minimumGapMinutes"]),
            float(rule["hardFloorMinutes"]),
            allowed_exceptions,
            reserved_pair_departures.get((origin, destination), []),
            maximum_patterns,
            beam_width,
        )
        LOGGER.info(
            "compiled %s pairing %d/%d %s-%s frequency=%d patterns=%d in %.1fs",
            fleet,
            type_index + 1,
            len(group_items),
            origin,
            destination,
            len(legs),
            len(patterns),
            time.monotonic() - pattern_started,
        )
        if not patterns:
            raise ValueError(
                f"No Section 2.6-compliant pattern exists for "
                f"{origin}-{destination}-{fleet}"
            )
        pattern_counts[f"{origin}-{destination}"] = len(patterns)
        for pattern in patterns:
            index = len(choices)
            choices.append(
                {
                    "type": type_index,
                    "events": pattern["events"],
                    "cost": float(pattern["cost"]),
                    "spacingExceptions": int(pattern["spacingExceptions"]),
                }
            )
            choices_by_type[type_index].append(index)

    arrivals: defaultdict[tuple[str, int], dict[int, float]] = defaultdict(dict)
    departures: defaultdict[tuple[str, int], dict[int, float]] = defaultdict(dict)
    bank_touches: defaultdict[tuple[str, str], dict[int, float]] = defaultdict(dict)
    station_events: defaultdict[str, set[int]] = defaultdict(set)

    def add_coefficient(row: dict[int, float], index: int, value: float = 1.0) -> None:
        row[index] = row.get(index, 0.0) + value

    objective = [float(choice["cost"]) for choice in choices]
    upper_bounds = [1.0] * len(choices)
    for index, choice in enumerate(choices):
        for event in choice["events"]:
            origin = str(event["origin"])
            destination = str(event["destination"])
            departure_utc = int(event["departureUtcMinute"])
            ready_utc = int(event["readyUtcMinute"])
            add_coefficient(departures[(origin, departure_utc)], index)
            add_coefficient(arrivals[(destination, ready_utc)], index)
            station_events[origin].add(departure_utc)
            station_events[destination].add(ready_utc)
            if event["originBankId"] is not None:
                add_coefficient(
                    bank_touches[(str(event["originBankId"]), "departure")],
                    index,
                )
            if event["destinationBankId"] is not None:
                add_coefficient(
                    bank_touches[(str(event["destinationBankId"]), "arrival")],
                    index,
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
    for type_index in range(len(group_items)):
        rows.append({index: 1.0 for index in choices_by_type[type_index]})
        lower_bounds.append(1.0)
        row_upper_bounds.append(1.0)

    bank_capacity_constraints = 0
    if bank_touch_limits is not None:
        if bank_touch_constraint not in {"exact", "capacity"}:
            raise ValueError("Bank-touch constraints require exact or capacity mode")
        for hub_windows in windows.values():
            for window in hub_windows:
                for operation in ("arrival", "departure"):
                    key = (str(window["id"]), operation)
                    rows.append(dict(bank_touches.get(key, {})))
                    limit = float(bank_touch_limits.get(key, 0))
                    lower_bounds.append(
                        limit if bank_touch_constraint == "exact" else 0.0
                    )
                    row_upper_bounds.append(limit)
                    bank_capacity_constraints += 1

    for station in sorted(station_events):
        events = sorted(station_events[station])
        for position, minute in enumerate(events):
            previous = events[position - 1]
            row = {
                q_by_event[(station, minute)]: 1.0,
                q_by_event[(station, previous)]: -1.0,
            }
            for index, value in arrivals[(station, minute)].items():
                row[index] = row.get(index, 0.0) - value
            for index, value in departures[(station, minute)].items():
                row[index] = row.get(index, 0.0) + value
            rows.append(row)
            lower_bounds.append(0.0)
            row_upper_bounds.append(0.0)

    capacity_row: dict[int, float] = {}
    for station, events in station_events.items():
        reference_minute = 0 if 0 in events else max(events)
        capacity_row[q_by_event[(station, reference_minute)]] = 1.0
    for index, choice in enumerate(choices):
        for event in choice["events"]:
            unavailable_minutes = int(event["blockMinutes"]) + minimum_turn
            departure_utc = int(event["departureUtcMinute"])
            if departure_utc == 0 or departure_utc + unavailable_minutes > 1440:
                add_coefficient(capacity_row, index)
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
        for index, value in departures[(station, boundary)].items():
            physical_presence[index] = physical_presence.get(index, 0.0) + value
        for index, choice in enumerate(choices):
            presence = sum(
                1
                for event in choice["events"]
                if event["destination"] == station
                and (
                    boundary - int(event["arrivalUtcMinute"])
                )
                % 1440
                < minimum_turn
            )
            if presence:
                physical_presence[index] = (
                    physical_presence.get(index, 0.0) + presence
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
    integrality = np.zeros(len(objective))
    integrality[: len(choices)] = 1.0
    for station, events in station_events.items():
        integrality[q_by_event[(station, min(events))]] = 1.0
    result = milp(
        # Pattern choices already compile the hard spacing rule.  Retain the
        # aircraft objective even in joint-bank feasibility mode so HiGHS has
        # a useful search direction toward the fixed fleet cap.
        c=np.asarray(objective),
        integrality=integrality,
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
            f"Exact {fleet} pairing-pattern materialization failed: {result.message}"
        )
    maximum_fraction = max(abs(value - round(value)) for value in result.x)
    if maximum_fraction > 1e-6:
        raise ValueError(
            f"Exact {fleet} pairing-pattern materialization returned fractional inventory"
        )

    materialized: dict[str, dict[str, Any]] = {}
    for type_index, (_, legs) in enumerate(group_items):
        selected = [
            index
            for index in choices_by_type[type_index]
            if int(round(result.x[index])) == 1
        ]
        if len(selected) != 1:
            raise ValueError(
                f"Exact {fleet} selected {len(selected)} patterns for type {type_index}"
            )
        selected_events = sorted(
            choices[selected[0]]["events"],
            key=lambda event: int(event["departureUtcMinute"]),
        )
        if len(selected_events) != len(legs):
            raise ValueError(
                f"Exact {fleet} pattern contains {len(selected_events)} of "
                f"{len(legs)} required legs"
            )
        for leg, event in zip(
            sorted(legs, key=lambda row: row["id"]), selected_events
        ):
            departure_utc = int(event["departureUtcMinute"])
            arrival_utc = departure_utc + int(leg["blockMinutes"])
            departure_local = _local_minute(departure_utc, leg["origin"], cities)
            arrival_local = _local_minute(arrival_utc, leg["destination"], cities)
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
        "timeVariables": len(choices),
        "inventoryVariables": len(q_by_event),
        "constraints": len(rows),
        "aircraftRequiredAtReference": int(aircraft_required),
        "assignedDestinationRons": len(assigned_rons),
        "objectiveMode": (
            "minimum_aircraft_with_fixed_cap"
            if feasibility_only
            else "minimum_aircraft"
        ),
        "pairingModel": "compiled_patterns",
        "maximumPatternsPerPairing": maximum_patterns,
        "generatedPatterns": len(choices),
        "minimumGeneratedPatterns": min(pattern_counts.values(), default=0),
        "maximumGeneratedPatterns": max(pattern_counts.values(), default=0),
        "bankCapacityConstraints": bank_capacity_constraints,
        "bankCapacityConstraintMode": bank_touch_constraint,
        "section26SpacingConstraints": "compiled_into_patterns",
        "section26PolicyExceptionCapacity": spacing_exception_capacity,
    }


def _expand_flexible_seed_types_to_markets(
    flexible_types: set[tuple[Any, ...]],
    group_items: list[
        tuple[tuple[Any, ...], list[dict[str, Any]]]
    ],
) -> set[tuple[Any, ...]]:
    """Allow both directions of a seed market to retime as one flow unit."""
    flexible_markets = {
        (str(key[0]), frozenset((str(key[1]), str(key[2]))))
        for key in flexible_types
    }
    return flexible_types | {
        key
        for key, _ in group_items
        if (
            str(key[0]),
            frozenset((str(key[1]), str(key[2]))),
        )
        in flexible_markets
    }


def _expand_flexible_seed_types_to_hub_operations(
    flexible_types: set[tuple[Any, ...]],
    seed_touches_by_type: dict[
        tuple[Any, ...], set[tuple[str, str]]
    ],
    seed_overflow_keys: set[tuple[str, str]],
    windows: dict[str, list[dict[str, Any]]],
) -> set[tuple[Any, ...]]:
    """Retiming closure for every seed type sharing an overloaded hub operation."""
    hub_by_bank = {
        str(window["id"]): str(hub)
        for hub, hub_windows in windows.items()
        for window in hub_windows
    }
    overflow_hub_operations = {
        (hub_by_bank[bank_id], operation)
        for bank_id, operation in seed_overflow_keys
        if bank_id in hub_by_bank
    }
    return flexible_types | {
        key
        for key, touches in seed_touches_by_type.items()
        if any(
            (hub_by_bank.get(bank_id), operation)
            in overflow_hub_operations
            for bank_id, operation in touches
        )
    }


def _cyclic_state_minute(events: set[int] | list[int], minute: int) -> int:
    """Return the latest event state at or before a cyclic daily boundary."""
    ordered = sorted(events)
    return max(
        (event for event in ordered if event <= minute),
        default=ordered[-1],
    )


def _materialized_physical_capacity_overflow(
    materialized: dict[str, dict[str, Any]],
    cities: dict[str, dict[str, Any]],
    minimum_turn: int,
) -> dict[tuple[str, int], int]:
    """Measure minimum cyclic ground inventory above gate-plus-stand capacity."""
    station_events: defaultdict[tuple[str, str], set[int]] = defaultdict(set)
    event_deltas: Counter[tuple[str, str, int]] = Counter()
    physical_events: defaultdict[str, set[int]] = defaultdict(set)
    arrivals_by_station: defaultdict[str, list[tuple[str, int]]] = defaultdict(list)
    for leg in materialized.values():
        fleet = str(leg["fleet"])
        origin = str(leg["origin"])
        destination = str(leg["destination"])
        departure = int(leg["departureUtcMinute"]) % 1440
        arrival = (departure + int(leg["blockMinutes"])) % 1440
        ready = (arrival + minimum_turn) % 1440
        station_events[(fleet, origin)].add(departure)
        station_events[(fleet, destination)].add(ready)
        event_deltas[(fleet, origin, departure)] -= 1
        event_deltas[(fleet, destination, ready)] += 1
        physical_events[origin].add(departure)
        physical_events[destination].add(arrival)
        arrivals_by_station[destination].append((fleet, arrival))

    inventory_states: dict[tuple[str, str, int], int] = {}
    for (fleet, station), event_set in station_events.items():
        events = sorted(event_set)
        values = {events[0]: 0}
        for previous, minute in zip(events, events[1:]):
            values[minute] = (
                values[previous] + event_deltas[(fleet, station, minute)]
            )
        shift = max(0, -min(values.values()))
        for minute, value in values.items():
            inventory_states[(fleet, station, minute)] = value + shift

    overflow: dict[tuple[str, int], int] = {}
    for station in physical_events:
        capacity = sum(_capacity(cities[station]))
        fleet_stations = [
            (fleet, event_set)
            for (fleet, candidate_station), event_set in station_events.items()
            if candidate_station == station
        ]
        for minute in range(1440):
            occupied = sum(
                inventory_states[
                    (
                        fleet,
                        station,
                        _cyclic_state_minute(event_set, minute),
                    )
                ]
                for fleet, event_set in fleet_stations
            )
            occupied += sum(
                1
                for _, arrival in arrivals_by_station[station]
                if (minute - arrival) % 1440 < minimum_turn
            )
            if occupied > capacity:
                overflow[(station, minute)] = occupied - capacity
    return overflow


def _materialized_passenger_gate_overflow(
    materialized: dict[str, dict[str, Any]],
    cities: dict[str, dict[str, Any]],
) -> dict[tuple[str, int], int]:
    """Measure the minimum passenger-gate demand implied by timed legs.

    Arrival and departure touch windows may belong to the same through-turn.
    Matching those touches by fleet gives a safe lower bound without assuming
    that a ready aircraft must occupy a gate throughout a long RON/ROD hold.
    The concrete successor allocator remains the final proof.
    """
    arrivals: defaultdict[str, list[tuple[str, int]]] = defaultdict(list)
    departures: defaultdict[str, list[tuple[str, int]]] = defaultdict(list)
    event_minutes: defaultdict[str, set[int]] = defaultdict(set)
    for leg in materialized.values():
        fleet = str(leg["fleet"])
        origin = str(leg["origin"])
        destination = str(leg["destination"])
        departure = int(leg["departureUtcMinute"]) % 1440
        arrival = (
            departure + int(leg["blockMinutes"])
        ) % 1440
        departures[origin].append((fleet, departure))
        arrivals[destination].append((fleet, arrival))
        event_minutes[origin].update(
            {
                (departure - TOUCH_DEPARTURE_MINUTES) % 1440,
                departure,
            }
        )
        event_minutes[destination].update(
            {
                arrival,
                (arrival + TOUCH_ARRIVAL_MINUTES) % 1440,
            }
        )

    overflow: dict[tuple[str, int], int] = {}
    for station, minutes in event_minutes.items():
        for minute in sorted(minutes):
            required = 0
            fleets = {
                fleet
                for fleet, _ in arrivals[station] + departures[station]
            }
            for fleet in fleets:
                arrival_touches = sum(
                    candidate_fleet == fleet
                    and (minute - arrival) % 1440
                    < TOUCH_ARRIVAL_MINUTES
                    for candidate_fleet, arrival in arrivals[station]
                )
                departure_touches = sum(
                    candidate_fleet == fleet
                    and 0
                    < (departure - minute) % 1440
                    <= TOUCH_DEPARTURE_MINUTES
                    for candidate_fleet, departure in departures[station]
                )
                required += max(arrival_touches, departure_touches)
            gates = _capacity(cities[station])[0]
            if required > gates:
                overflow[(station, minute)] = required - gates
    return overflow


def _capacity_repair_stations(
    physical_overflow: dict[tuple[str, int], int],
    passenger_gate_overflow: dict[tuple[str, int], int],
) -> set[str]:
    """Select every station whose passenger touches need exact retiming.

    Physical gate-plus-stand overflow can make a large model unnecessarily
    broad, so repair retains the existing largest-station bound there. A
    passenger-gate overflow is different: leaving even one affected station's
    market types fixed guarantees that PHOS can survive an otherwise optimal
    repair. Every passenger-overloaded station must therefore be flexible.
    """
    physical_by_station: defaultdict[str, list[int]] = defaultdict(list)
    for (station, _), overflow in physical_overflow.items():
        physical_by_station[station].append(overflow)
    selected = {
        station
        for station, _ in sorted(
            physical_by_station.items(),
            key=lambda item: (
                -max(item[1]),
                -sum(item[1]),
                item[0],
            ),
        )[:1]
    }

    passenger_by_station: defaultdict[str, list[int]] = defaultdict(list)
    for (station, _), overflow in passenger_gate_overflow.items():
        passenger_by_station[station].append(overflow)
    selected.update(passenger_by_station)
    return selected


def _materialized_gate_assignments(
    materialized: dict[str, dict[str, Any]],
    successors: dict[str, str],
    cities: dict[str, dict[str, Any]],
    minimum_turn: int,
) -> tuple[dict[str, list[tuple[GateClaim, int]]], dict[str, Any]]:
    """Assign real successor holds to fixed gates and stands.

    Unlike the aggregate inventory lower bound, this evaluates the actual
    arrival-to-next-departure connection selected for each aircraft cycle.
    Long RON/ROD holds may be split, but every passenger touch must remain at
    a gate and no row may exceed the configured physical inventory.
    """
    claims_by_station: defaultdict[str, list[GateClaim]] = defaultdict(list)
    for identifier, successor in successors.items():
        leg = materialized[identifier]
        following = materialized[successor]
        station = str(leg["destination"])
        arrival_utc = int(leg["departureUtcMinute"]) + int(
            leg["blockMinutes"]
        )
        wait = _connection_wait(
            arrival_utc,
            int(following["departureUtcMinute"]),
            minimum_turn,
        )
        start = _local_minute(arrival_utc, station, cities)
        claims_by_station[station].append(
            GateClaim(
                start,
                start + wait,
                f"{identifier} -> {successor}",
                str(leg["fleet"]),
                "ron" if wait >= 360 else "turn",
                str(leg["origin"]),
                str(following["destination"]),
            )
        )

    assignments: dict[str, list[tuple[GateClaim, int]]] = {}
    failures = []
    tow_count = 0
    for station in sorted(claims_by_station):
        gates, stands = _capacity(cities[station])
        try:
            station_assignments, stand_middles = assign_gates(
                claims_by_station[station],
                gates,
                n_stands=stands,
                return_provenance=True,
            )
        except GateCapacityError as error:
            failures.append(
                {
                    "station": station,
                    "message": str(error),
                    "requiredGates": error.required_gates,
                    "configuredGates": error.configured_gates,
                    "requiredStands": error.required_stands,
                    "configuredStands": error.configured_stands,
                    "strandedPassengerTouches": len(error.stranded_touches),
                    "strandedLabels": sorted(
                        claim.label for claim in error.stranded_touches
                    ),
                }
            )
            continue
        assignments[station] = station_assignments
        tow_count += len(stand_middles)
    return assignments, {
        "status": "pass" if not failures else "fail",
        "stations": len(claims_by_station),
        "towMovements": tow_count,
        "failures": failures,
    }


def _solve_all_fleets_with_pairing_patterns(
    inventory: dict[str, list[dict[str, Any]]],
    fleet_counts: dict[str, int],
    assigned_rons: dict[str, list[str]],
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    windows: dict[str, list[dict[str, Any]]],
    targets: dict[str, dict[str, list[int]]],
    pairing_departure_counts: Counter[tuple[str, str]],
    station_departure_counts: Counter[str],
    bank_touch_limits: dict[tuple[str, str], int],
    allow_pairing_spacing_exceptions: bool,
    time_limit_seconds: int,
    maximum_patterns: int,
    beam_width: int,
    seed_materialized: dict[str, dict[str, Any]] | None = None,
    enforce_passenger_gate_capacity: bool = False,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    """Jointly choose every fleet's patterns against one bank-capacity ledger."""
    global_started = time.monotonic()
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    grouped: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for fleet, copies in inventory.items():
        for leg in copies:
            if leg.get("originBankId") is not None or leg.get("destinationBankId") is not None:
                raise ValueError(
                    "Global pairing-pattern materialization requires joint bank assignment"
                )
            grouped[
                (
                    fleet,
                    leg["origin"],
                    leg["destination"],
                    leg["classification"],
                    int(leg["blockMinutes"]),
                )
            ].append(leg)
    group_items = sorted(grouped.items())
    pairings = [(str(key[1]), str(key[2])) for key, _ in group_items]
    if len(pairings) != len(set(pairings)):
        raise ValueError(
            "Global pairing-pattern inventory requires one fleet per directional market"
        )

    seed_departures: defaultdict[tuple[Any, ...], list[int]] = defaultdict(list)
    seed_bank_usage: Counter[tuple[str, str]] = Counter()
    seed_touches_by_type: defaultdict[
        tuple[Any, ...], set[tuple[str, str]]
    ] = defaultdict(set)
    seed_overflow_keys: set[tuple[str, str]] = set()
    seed_physical_capacity_overflow: dict[tuple[str, int], int] = {}
    seed_passenger_gate_overflow: dict[tuple[str, int], int] = {}
    flexible_seed_types: set[tuple[Any, ...]] = set()
    if seed_materialized is not None:
        for leg in seed_materialized.values():
            key = (
                str(leg["fleet"]),
                str(leg["origin"]),
                str(leg["destination"]),
                str(leg["classification"]),
                int(leg["blockMinutes"]),
            )
            seed_departures[key].append(int(leg["departureUtcMinute"]))
            if leg.get("originBankId") is not None:
                touch = (str(leg["originBankId"]), "departure")
                seed_bank_usage[touch] += 1
                seed_touches_by_type[key].add(touch)
            if leg.get("destinationBankId") is not None:
                touch = (str(leg["destinationBankId"]), "arrival")
                seed_bank_usage[touch] += 1
                seed_touches_by_type[key].add(touch)
        seed_overflow_keys = {
            key
            for key, touches in seed_bank_usage.items()
            if touches > int(bank_touch_limits[key])
        }
        for key, touches in seed_touches_by_type.items():
            if touches & seed_overflow_keys:
                flexible_seed_types.add(key)
        directly_flexible_types = len(flexible_seed_types)
        hub_operation_flexible_types = directly_flexible_types
        if (
            len(seed_overflow_keys)
            <= HUB_OPERATION_CLOSURE_MAX_OVERFLOW_ROWS
        ):
            flexible_seed_types = (
                _expand_flexible_seed_types_to_hub_operations(
                    flexible_seed_types,
                    dict(seed_touches_by_type),
                    seed_overflow_keys,
                    windows,
                )
            )
            hub_operation_flexible_types = len(flexible_seed_types)
        flexible_seed_types = _expand_flexible_seed_types_to_markets(
            flexible_seed_types,
            group_items,
        )
        seed_physical_capacity_overflow = (
            _materialized_physical_capacity_overflow(
                seed_materialized,
                cities,
                minimum_turn,
            )
        )
        if enforce_passenger_gate_capacity:
            seed_passenger_gate_overflow = (
                _materialized_passenger_gate_overflow(
                    seed_materialized,
                    cities,
                )
            )
        overloaded_stations = _capacity_repair_stations(
            seed_physical_capacity_overflow,
            seed_passenger_gate_overflow,
        )
        flexible_seed_types.update(
            key
            for key, _ in group_items
            if str(key[1]) in overloaded_stations
            or str(key[2]) in overloaded_stations
        )
        LOGGER.info(
            "global seed overflow bank_rows=%d bank_touches=%d airport_rows=%d passenger_gate_rows=%d selected_airports=%s; flexible types=%d direct, %d with hub-operation closure, %d total",
            len(seed_overflow_keys),
            sum(
                max(0, touches - int(bank_touch_limits[key]))
                for key, touches in seed_bank_usage.items()
            ),
            len(seed_physical_capacity_overflow),
            len(seed_passenger_gate_overflow),
            ",".join(sorted(overloaded_stations)) or "none",
            directly_flexible_types,
            hub_operation_flexible_types,
            len(flexible_seed_types),
        )
        for times in seed_departures.values():
            times.sort()

    section26 = policy["section26"]
    hubs = set(policy["hubs"])
    choices: list[dict[str, Any]] = []
    choices_by_type: defaultdict[int, list[int]] = defaultdict(list)
    choices_by_fleet: defaultdict[str, list[int]] = defaultdict(list)
    seed_choice_by_type: dict[int, int] = {}
    types_by_fleet: Counter[str] = Counter()
    pattern_counts_by_fleet: defaultdict[str, list[int]] = defaultdict(list)
    spacing_capacity_by_fleet: Counter[str] = Counter()
    for type_index, (key, legs) in enumerate(group_items):
        fleet, origin, destination, classification, block = key
        types_by_fleet[fleet] += 1
        candidates = []
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
            candidates.append(
                {
                    "fleet": fleet,
                    "origin": origin,
                    "destination": destination,
                    "classification": classification,
                    "blockMinutes": block,
                    "departureUtcMinute": departure_utc,
                    "arrivalUtcMinute": arrival_utc,
                    "readyUtcMinute": (
                        departure_utc + block + minimum_turn
                    )
                    % 1440,
                    "originBankId": (
                        _bank_id(departure_local, windows[origin])
                        if origin in windows
                        else None
                    ),
                    "destinationBankId": (
                        _bank_id(arrival_local, windows[destination])
                        if destination in windows
                        else None
                    ),
                    "cost": _timing_cost(
                        origin,
                        destination,
                        departure_utc,
                        arrival_utc,
                        cities,
                        targets,
                    ),
                }
            )
        rule = pairing_spacing_rule(
            origin,
            destination,
            int(pairing_departure_counts[(origin, destination)]),
            int(station_departure_counts[origin]),
            hubs,
            section26,
        )
        allowed_exceptions = (
            int(rule["allowedExceptions"])
            if allow_pairing_spacing_exceptions
            else 0
        )
        spacing_capacity_by_fleet[fleet] += allowed_exceptions
        seed_times = tuple(seed_departures.get(key, []))
        patterns = (
            []
            if seed_materialized is not None
            and key not in flexible_seed_types
            else _pairing_patterns(
                candidates,
                len(legs),
                float(rule["minimumGapMinutes"]),
                float(rule["hardFloorMinutes"]),
                allowed_exceptions,
                [],
                maximum_patterns,
                beam_width,
            )
        )
        if seed_materialized is not None:
            matching_seed = [
                pattern
                for pattern in patterns
                if tuple(
                    int(event["departureUtcMinute"])
                    for event in pattern["events"]
                )
                == seed_times
            ]
            if not matching_seed:
                candidates_by_minute = {
                    int(candidate["departureUtcMinute"]): candidate
                    for candidate in candidates
                }
                if len(seed_times) != len(legs) or any(
                    minute not in candidates_by_minute for minute in seed_times
                ):
                    raise ValueError(
                        f"Constructive seed uses an unavailable time for "
                        f"{origin}-{destination}-{fleet}"
                    )
                distances = [
                    _circular_distance(first, second)
                    for position, first in enumerate(seed_times)
                    for second in seed_times[position + 1 :]
                ]
                if any(
                    distance < float(rule["hardFloorMinutes"])
                    for distance in distances
                ):
                    raise ValueError(
                        f"Constructive seed misses the hard spacing floor for "
                        f"{origin}-{destination}-{fleet}"
                    )
                seed_exceptions = sum(
                    float(rule["hardFloorMinutes"])
                    <= distance
                    < float(rule["minimumGapMinutes"])
                    for distance in distances
                )
                if seed_exceptions > allowed_exceptions:
                    raise ValueError(
                        f"Constructive seed exceeds the spacing exception allowance for "
                        f"{origin}-{destination}-{fleet}"
                    )
                seed_pattern = {
                    "events": tuple(
                        candidates_by_minute[minute] for minute in seed_times
                    ),
                    "cost": sum(
                        float(candidates_by_minute[minute]["cost"])
                        for minute in seed_times
                    )
                    + SPACING_EXCEPTION_OBJECTIVE_WEIGHT * seed_exceptions,
                    "spacingExceptions": seed_exceptions,
                }
                patterns.append(seed_pattern)
                matching_seed = [seed_pattern]
            if key not in flexible_seed_types:
                patterns = matching_seed
        if not patterns:
            raise ValueError(
                f"No Section 2.6-compliant pattern exists for "
                f"{origin}-{destination}-{fleet}"
            )
        pattern_counts_by_fleet[fleet].append(len(patterns))
        for pattern in patterns:
            pattern_times = tuple(
                int(event["departureUtcMinute"])
                for event in pattern["events"]
            )
            index = len(choices)
            choices.append(
                {
                    "type": type_index,
                    "fleet": fleet,
                    "events": pattern["events"],
                    "cost": float(pattern["cost"])
                    + (
                        SEED_DEVIATION_OBJECTIVE_WEIGHT
                        if seed_materialized is not None
                        and pattern_times != seed_times
                        else 0.0
                    ),
                    "spacingExceptions": int(pattern["spacingExceptions"]),
                }
            )
            choices_by_type[type_index].append(index)
            choices_by_fleet[fleet].append(index)
            if seed_materialized is not None and pattern_times == seed_times:
                seed_choice_by_type[type_index] = index

    LOGGER.info(
        "compiled global repair patterns types=%d choices=%d in %.1fs",
        len(group_items),
        len(choices),
        time.monotonic() - global_started,
    )

    arrivals: defaultdict[
        tuple[str, str, int], dict[int, float]
    ] = defaultdict(dict)
    departures: defaultdict[
        tuple[str, str, int], dict[int, float]
    ] = defaultdict(dict)
    bank_touches: defaultdict[
        tuple[str, str], dict[int, float]
    ] = defaultdict(dict)
    station_events: defaultdict[tuple[str, str], set[int]] = defaultdict(set)
    physical_station_events: defaultdict[str, set[int]] = defaultdict(set)
    passenger_gate_events: defaultdict[str, set[int]] = defaultdict(set)
    arrival_events_by_station: defaultdict[
        str, list[tuple[int, str, int]]
    ] = defaultdict(list)
    departure_events_by_station: defaultdict[
        str, list[tuple[int, str, int]]
    ] = defaultdict(list)

    def add_coefficient(row: dict[int, float], index: int, value: float = 1.0) -> None:
        row[index] = row.get(index, 0.0) + value

    objective = [float(choice["cost"]) for choice in choices]
    upper_bounds = [1.0] * len(choices)
    for index, choice in enumerate(choices):
        fleet = str(choice["fleet"])
        for event in choice["events"]:
            origin = str(event["origin"])
            destination = str(event["destination"])
            departure_utc = int(event["departureUtcMinute"])
            arrival_utc = int(event["arrivalUtcMinute"])
            ready_utc = int(event["readyUtcMinute"])
            add_coefficient(
                departures[(fleet, origin, departure_utc)], index
            )
            add_coefficient(
                arrivals[(fleet, destination, ready_utc)], index
            )
            station_events[(fleet, origin)].add(departure_utc)
            station_events[(fleet, destination)].add(ready_utc)
            physical_station_events[origin].add(departure_utc)
            physical_station_events[destination].add(arrival_utc)
            passenger_gate_events[origin].update(
                {
                    (departure_utc - TOUCH_DEPARTURE_MINUTES) % 1440,
                    departure_utc,
                }
            )
            passenger_gate_events[destination].update(
                {
                    arrival_utc,
                    (arrival_utc + TOUCH_ARRIVAL_MINUTES) % 1440,
                }
            )
            arrival_events_by_station[destination].append(
                (index, fleet, arrival_utc)
            )
            departure_events_by_station[origin].append(
                (index, fleet, departure_utc)
            )
            if event["originBankId"] is not None:
                add_coefficient(
                    bank_touches[(str(event["originBankId"]), "departure")],
                    index,
                )
            if event["destinationBankId"] is not None:
                add_coefficient(
                    bank_touches[(str(event["destinationBankId"]), "arrival")],
                    index,
                )

    q_by_event: dict[tuple[str, str, int], int] = {}
    for fleet, station in sorted(station_events):
        for minute in sorted(station_events[(fleet, station)]):
            q_by_event[(fleet, station, minute)] = len(objective)
            objective.append(0.0)
            upper_bounds.append(float(fleet_counts[fleet]))

    rows: list[dict[int, float]] = []
    lower_bounds: list[float] = []
    row_upper_bounds: list[float] = []
    for type_index in range(len(group_items)):
        rows.append({index: 1.0 for index in choices_by_type[type_index]})
        lower_bounds.append(1.0)
        row_upper_bounds.append(1.0)

    bank_capacity_constraints = 0
    bank_overflow_variables: dict[tuple[str, str], int] = {}
    for hub_windows in windows.values():
        for window in hub_windows:
            for operation in ("arrival", "departure"):
                key = (str(window["id"]), operation)
                overflow_index = len(objective)
                objective.append(BANK_OVERFLOW_OBJECTIVE_WEIGHT)
                upper_bounds.append(
                    float(sum(bank_touches.get(key, {}).values()))
                )
                bank_overflow_variables[key] = overflow_index
                row = dict(bank_touches.get(key, {}))
                row[overflow_index] = -1.0
                rows.append(row)
                lower_bounds.append(0.0)
                row_upper_bounds.append(float(bank_touch_limits[key]))
                bank_capacity_constraints += 1

    physical_capacity_constraints = 0
    physical_capacity_rows: dict[tuple[str, int], dict[int, float]] = {}
    physical_capacity_overflow_variables: dict[str, int] = {}
    for station in sorted(physical_station_events):
        combined_capacity = float(sum(_capacity(cities[station])))
        overflow_index = len(objective)
        objective.append(BANK_OVERFLOW_OBJECTIVE_WEIGHT)
        upper_bounds.append(float(sum(fleet_counts.values())))
        physical_capacity_overflow_variables[station] = overflow_index
        fleet_station_events = [
            (fleet, event_set)
            for (fleet, candidate_station), event_set in station_events.items()
            if candidate_station == station
        ]
        for minute in sorted(physical_station_events[station]):
            row = {
                q_by_event[
                    (
                        fleet,
                        station,
                        _cyclic_state_minute(event_set, minute),
                    )
                ]: 1.0
                for fleet, event_set in fleet_station_events
            }
            for index, _, arrival_utc in arrival_events_by_station[station]:
                if (minute - arrival_utc) % 1440 < minimum_turn:
                    add_coefficient(row, index)
            physical_capacity_rows[(station, minute)] = dict(row)
            row[overflow_index] = -1.0
            rows.append(row)
            lower_bounds.append(-np.inf)
            row_upper_bounds.append(combined_capacity)
            physical_capacity_constraints += 1

    passenger_gate_constraints = 0
    passenger_touch_variables: dict[tuple[str, int, str], int] = {}
    passenger_arrival_rows: dict[
        tuple[str, int, str], dict[int, float]
    ] = {}
    passenger_departure_rows: dict[
        tuple[str, int, str], dict[int, float]
    ] = {}
    passenger_gate_rows: dict[tuple[str, int], dict[int, float]] = {}
    passenger_gate_overflow_variables: dict[str, int] = {}
    if enforce_passenger_gate_capacity:
        for station in sorted(passenger_gate_events):
            overflow_index = len(objective)
            objective.append(BANK_OVERFLOW_OBJECTIVE_WEIGHT)
            upper_bounds.append(float(sum(fleet_counts.values())))
            passenger_gate_overflow_variables[station] = overflow_index
            station_fleets = sorted(
                {
                    fleet
                    for _, fleet, _ in (
                        arrival_events_by_station[station]
                        + departure_events_by_station[station]
                    )
                }
            )
            for minute in sorted(passenger_gate_events[station]):
                gate_row: dict[int, float] = {}
                for fleet in station_fleets:
                    key = (station, minute, fleet)
                    touch_index = len(objective)
                    objective.append(0.0)
                    upper_bounds.append(float(fleet_counts[fleet]))
                    passenger_touch_variables[key] = touch_index
                    arrival_row: dict[int, float] = {}
                    for index, candidate_fleet, arrival_utc in (
                        arrival_events_by_station[station]
                    ):
                        if (
                            candidate_fleet == fleet
                            and (minute - arrival_utc) % 1440
                            < TOUCH_ARRIVAL_MINUTES
                        ):
                            add_coefficient(arrival_row, index)
                    departure_row: dict[int, float] = {}
                    for index, candidate_fleet, departure_utc in (
                        departure_events_by_station[station]
                    ):
                        until_departure = (departure_utc - minute) % 1440
                        if (
                            candidate_fleet == fleet
                            and 0
                            < until_departure
                            <= TOUCH_DEPARTURE_MINUTES
                        ):
                            add_coefficient(departure_row, index)
                    passenger_arrival_rows[key] = arrival_row
                    passenger_departure_rows[key] = departure_row
                    for touch_row in (arrival_row, departure_row):
                        row = {touch_index: 1.0}
                        for index, value in touch_row.items():
                            add_coefficient(row, index, -value)
                        rows.append(row)
                        lower_bounds.append(0.0)
                        row_upper_bounds.append(np.inf)
                        passenger_gate_constraints += 1
                    gate_row[touch_index] = 1.0
                passenger_gate_rows[(station, minute)] = dict(gate_row)
                gate_row[overflow_index] = -1.0
                rows.append(gate_row)
                lower_bounds.append(-np.inf)
                row_upper_bounds.append(float(_capacity(cities[station])[0]))
                passenger_gate_constraints += 1

    for fleet, station in sorted(station_events):
        events = sorted(station_events[(fleet, station)])
        for position, minute in enumerate(events):
            previous = events[position - 1]
            row = {
                q_by_event[(fleet, station, minute)]: 1.0,
                q_by_event[(fleet, station, previous)]: -1.0,
            }
            for index, value in arrivals[(fleet, station, minute)].items():
                row[index] = row.get(index, 0.0) - value
            for index, value in departures[(fleet, station, minute)].items():
                row[index] = row.get(index, 0.0) + value
            rows.append(row)
            lower_bounds.append(0.0)
            row_upper_bounds.append(0.0)

    capacity_rows: dict[str, dict[int, float]] = {}
    for fleet in sorted(fleet_counts):
        capacity_row: dict[int, float] = {}
        for candidate_fleet, station in station_events:
            if candidate_fleet != fleet:
                continue
            events = station_events[(fleet, station)]
            reference_minute = 0 if 0 in events else max(events)
            capacity_row[q_by_event[(fleet, station, reference_minute)]] = 1.0
        for index in choices_by_fleet[fleet]:
            for event in choices[index]["events"]:
                unavailable_minutes = int(event["blockMinutes"]) + minimum_turn
                departure_utc = int(event["departureUtcMinute"])
                if departure_utc == 0 or departure_utc + unavailable_minutes > 1440:
                    add_coefficient(capacity_row, index)
        rows.append(capacity_row)
        lower_bounds.append(0.0)
        row_upper_bounds.append(float(fleet_counts[fleet]))
        capacity_rows[fleet] = capacity_row

    ron_constraints_by_fleet: Counter[str] = Counter()
    for fleet, stations in sorted(assigned_rons.items()):
        for station in stations:
            boundary = _utc_minute(180, station, cities)
            events = sorted(station_events[(fleet, station)])
            state_minute = (
                boundary
                if boundary in station_events[(fleet, station)]
                else max(
                    (minute for minute in events if minute < boundary),
                    default=max(events),
                )
            )
            physical_presence = {
                q_by_event[(fleet, station, state_minute)]: 1.0
            }
            for index, value in departures[(fleet, station, boundary)].items():
                physical_presence[index] = (
                    physical_presence.get(index, 0.0) + value
                )
            for index in choices_by_fleet[fleet]:
                presence = sum(
                    1
                    for event in choices[index]["events"]
                    if event["destination"] == station
                    and (
                        boundary - int(event["arrivalUtcMinute"])
                    )
                    % 1440
                    < minimum_turn
                )
                if presence:
                    physical_presence[index] = (
                        physical_presence.get(index, 0.0) + presence
                    )
            rows.append(physical_presence)
            lower_bounds.append(1.0)
            row_upper_bounds.append(np.inf)
            ron_constraints_by_fleet[fleet] += 1

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
    integrality = np.zeros(len(objective))
    integrality[: len(choices)] = 1.0
    for fleet, station in station_events:
        integrality[
            q_by_event[(fleet, station, min(station_events[(fleet, station)]))]
        ] = 1.0
    objective_array = np.asarray(objective)
    lower_array = np.zeros(len(objective))
    upper_array = np.asarray(upper_bounds)
    row_lower_array = np.asarray(lower_bounds)
    row_upper_array = np.asarray(row_upper_bounds)
    if seed_materialized is not None:
        if len(seed_choice_by_type) != len(group_items):
            raise ValueError(
                "Constructive seed does not select every directional leg type"
            )
        mip_start = np.zeros(len(objective))
        selected_choice_indices = set(seed_choice_by_type.values())
        for index in selected_choice_indices:
            mip_start[index] = 1.0
        event_deltas: Counter[tuple[str, str, int]] = Counter()
        for index in selected_choice_indices:
            fleet = str(choices[index]["fleet"])
            for event in choices[index]["events"]:
                event_deltas[
                    (fleet, str(event["origin"]), int(event["departureUtcMinute"]))
                ] -= 1
                event_deltas[
                    (fleet, str(event["destination"]), int(event["readyUtcMinute"]))
                ] += 1
        for fleet, station in station_events:
            events = sorted(station_events[(fleet, station)])
            values = {events[0]: 0.0}
            for minute in events[1:]:
                previous = events[events.index(minute) - 1]
                values[minute] = values[previous] + float(
                    event_deltas[(fleet, station, minute)]
                )
            shift = max(0.0, -min(values.values()))
            for minute, value in values.items():
                mip_start[q_by_event[(fleet, station, minute)]] = value + shift
        for key, overflow_index in bank_overflow_variables.items():
            touches = sum(
                value
                for index, value in bank_touches.get(key, {}).items()
                if index in selected_choice_indices
            )
            mip_start[overflow_index] = max(
                0.0, touches - float(bank_touch_limits[key])
            )
        for station, overflow_index in physical_capacity_overflow_variables.items():
            maximum_overflow = max(
                (
                    sum(
                        value * mip_start[index]
                        for index, value in row.items()
                    )
                    - float(sum(_capacity(cities[station])))
                    for (candidate_station, _), row in physical_capacity_rows.items()
                    if candidate_station == station
                ),
                default=0.0,
            )
            mip_start[overflow_index] = max(
                0.0,
                maximum_overflow,
            )
        for key, touch_index in passenger_touch_variables.items():
            arrival_touches = sum(
                value
                for index, value in passenger_arrival_rows[key].items()
                if index in selected_choice_indices
            )
            departure_touches = sum(
                value
                for index, value in passenger_departure_rows[key].items()
                if index in selected_choice_indices
            )
            mip_start[touch_index] = max(
                arrival_touches,
                departure_touches,
            )
        for station, overflow_index in (
            passenger_gate_overflow_variables.items()
        ):
            maximum_overflow = max(
                (
                    sum(
                        value * mip_start[index]
                        for index, value in row.items()
                    )
                    - float(_capacity(cities[station])[0])
                    for (candidate_station, _), row in (
                        passenger_gate_rows.items()
                    )
                    if candidate_station == station
                ),
                default=0.0,
            )
            mip_start[overflow_index] = max(0.0, maximum_overflow)
        row_values = np.asarray(matrix @ mip_start).reshape(-1)
        lower_violation = np.max(
            np.maximum(row_lower_array - row_values, 0.0), initial=0.0
        )
        upper_violation = np.max(
            np.maximum(row_values - row_upper_array, 0.0), initial=0.0
        )
        bound_violation = max(
            float(np.max(np.maximum(lower_array - mip_start, 0.0), initial=0.0)),
            float(np.max(np.maximum(mip_start - upper_array, 0.0), initial=0.0)),
        )
        if max(lower_violation, upper_violation, bound_violation) > 1e-6:
            raise ValueError(
                "Constructive MIP start is invalid: "
                f"row lower {lower_violation:.6f}, row upper {upper_violation:.6f}, "
                f"bound {bound_violation:.6f}"
            )
        LOGGER.info(
            "starting global repair variables=%d constraints=%d time_limit=%ds",
            len(objective),
            len(rows),
            time_limit_seconds,
        )
        result = _milp_with_start(
            objective_array,
            integrality,
            lower_array,
            upper_array,
            matrix,
            row_lower_array,
            row_upper_array,
            mip_start,
            time_limit_seconds,
        )
    else:
        result = milp(
            c=objective_array,
            integrality=integrality,
            bounds=Bounds(lower_array, upper_array),
            constraints=LinearConstraint(
                matrix,
                row_lower_array,
                row_upper_array,
            ),
            options={
                "time_limit": time_limit_seconds,
                "mip_rel_gap": MIP_RELATIVE_GAP,
            },
        )
    if result.x is None:
        raise ValueError(
            "Exact global pairing-pattern materialization failed: "
            + str(result.message)
        )
    bank_overflow = {
        f"{bank_id}:{operation}": float(result.x[index])
        for (bank_id, operation), index in bank_overflow_variables.items()
        if float(result.x[index]) > 1e-6
    }
    physical_capacity_overflow = {
        station: float(result.x[index])
        for station, index in physical_capacity_overflow_variables.items()
        if float(result.x[index]) > 1e-6
    }
    passenger_gate_overflow = {
        station: float(result.x[index])
        for station, index in passenger_gate_overflow_variables.items()
        if float(result.x[index]) > 1e-6
    }
    LOGGER.info(
        "global repair returned %s with %.0f bank overflow, %.0f airport overflow, and %.0f passenger-gate overflow in %.1fs",
        result.message,
        sum(bank_overflow.values()),
        sum(physical_capacity_overflow.values()),
        sum(passenger_gate_overflow.values()),
        time.monotonic() - global_started,
    )
    maximum_fraction = max(abs(value - round(value)) for value in result.x)
    if maximum_fraction > 1e-6:
        raise ValueError(
            "Exact global pairing-pattern materialization returned fractional inventory"
        )

    materialized: dict[str, dict[str, Any]] = {}
    for type_index, (key, legs) in enumerate(group_items):
        fleet = str(key[0])
        selected = [
            index
            for index in choices_by_type[type_index]
            if int(round(result.x[index])) == 1
        ]
        if len(selected) != 1:
            raise ValueError(
                f"Exact global solve selected {len(selected)} patterns for type {type_index}"
            )
        selected_events = sorted(
            choices[selected[0]]["events"],
            key=lambda event: int(event["departureUtcMinute"]),
        )
        if len(selected_events) != len(legs):
            raise ValueError(
                f"Exact {fleet} pattern contains {len(selected_events)} of "
                f"{len(legs)} required legs"
            )
        for leg, event in zip(
            sorted(legs, key=lambda row: row["id"]), selected_events
        ):
            departure_utc = int(event["departureUtcMinute"])
            arrival_utc = departure_utc + int(leg["blockMinutes"])
            departure_local = _local_minute(departure_utc, leg["origin"], cities)
            arrival_local = _local_minute(arrival_utc, leg["destination"], cities)
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

    solver_fleets: dict[str, dict[str, Any]] = {}
    for fleet in sorted(fleet_counts):
        pattern_counts = pattern_counts_by_fleet[fleet]
        aircraft_required = round(
            sum(
                result.x[index] * value
                for index, value in capacity_rows[fleet].items()
            )
        )
        solver_fleets[fleet] = {
            "status": (
                "optimal_within_gap" if result.success else "feasible_time_limit"
            ),
            "message": str(result.message),
            "mipGap": round(float(getattr(result, "mip_gap", 0.0) or 0.0), 9),
            "legTypes": int(types_by_fleet[fleet]),
            "timeVariables": len(choices_by_fleet[fleet]),
            "inventoryVariables": sum(
                len(events)
                for (candidate_fleet, _), events in station_events.items()
                if candidate_fleet == fleet
            ),
            "constraints": len(rows),
            "aircraftRequiredAtReference": int(aircraft_required),
            "assignedDestinationRons": int(ron_constraints_by_fleet[fleet]),
            "objectiveMode": "global_minimum_aircraft_with_fixed_fleet_caps",
            "pairingModel": "compiled_patterns",
            "maximumPatternsPerPairing": maximum_patterns,
            "generatedPatterns": len(choices_by_fleet[fleet]),
            "minimumGeneratedPatterns": min(pattern_counts, default=0),
            "maximumGeneratedPatterns": max(pattern_counts, default=0),
            "bankCapacityConstraints": bank_capacity_constraints,
            "bankCapacityConstraintMode": "global_capacity",
            "physicalCapacityConstraints": physical_capacity_constraints,
            "physicalCapacityConstraintMode": "global_gate_plus_stand_capacity",
            "passengerGateConstraints": passenger_gate_constraints,
            "passengerGateConstraintMode": (
                "fleet_matched_arrival_departure_touch_windows"
                if enforce_passenger_gate_capacity
                else "disabled"
            ),
            "section26SpacingConstraints": "compiled_into_patterns",
            "section26PolicyExceptionCapacity": int(
                spacing_capacity_by_fleet[fleet]
            ),
        }
    joint_solver = {
        "status": (
            "repair_incomplete_time_limit"
            if (
                bank_overflow
                or physical_capacity_overflow
                or passenger_gate_overflow
            )
            else "optimal_within_gap" if result.success else "feasible_time_limit"
        ),
        "message": str(result.message),
        "mipGap": round(float(getattr(result, "mip_gap", 0.0) or 0.0), 9),
        "timeVariables": len(choices),
        "inventoryVariables": len(q_by_event),
        "constraints": len(rows),
        "bankCapacityConstraints": bank_capacity_constraints,
        "bankFeasibilityOverflow": sum(bank_overflow.values()),
        "bankOverflowRows": bank_overflow,
        "physicalCapacityConstraints": physical_capacity_constraints,
        "physicalCapacityFeasibilityOverflow": sum(
            physical_capacity_overflow.values()
        ),
        "physicalCapacityOverflowRows": physical_capacity_overflow,
        "passengerGateConstraints": passenger_gate_constraints,
        "passengerGateFeasibilityOverflow": sum(
            passenger_gate_overflow.values()
        ),
        "passengerGateOverflowRows": passenger_gate_overflow,
        "constructiveSeed": seed_materialized is not None,
        "seedOverloadedBankRows": len(seed_overflow_keys),
        "seedOverloadedPhysicalCapacityRows": len(
            seed_physical_capacity_overflow
        ),
        "seedOverloadedPassengerGateRows": len(
            seed_passenger_gate_overflow
        ),
        "seedFlexibleLegTypes": len(flexible_seed_types),
        "timeLimitSeconds": time_limit_seconds,
    }
    return materialized, solver_fleets, joint_solver


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
    bank_touch_limits: dict[tuple[str, str], int] | None,
    bank_touch_constraint: str | None,
    feasibility_only: bool,
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
                leg.get("originBankId"),
                leg.get("destinationBankId"),
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
    bank_touches: defaultdict[tuple[str, str], list[int]] = defaultdict(list)
    station_events: defaultdict[str, set[int]] = defaultdict(set)
    objective: list[float] = []
    upper_bounds: list[float] = []

    for type_index, (key, legs) in enumerate(group_items):
        (
            origin,
            destination,
            classification,
            block,
            origin_bank_id,
            destination_bank_id,
        ) = key
        origin_windows = windows.get(origin, [])
        destination_windows = windows.get(destination, [])
        if origin_bank_id is not None:
            origin_windows = [
                window
                for window in origin_windows
                if window["id"] == origin_bank_id
            ]
            if not origin_windows:
                raise ValueError(
                    f"Assigned origin bank {origin_bank_id} is missing for {origin}"
                )
        if destination_bank_id is not None:
            destination_windows = [
                window
                for window in destination_windows
                if window["id"] == destination_bank_id
            ]
            if not destination_windows:
                raise ValueError(
                    f"Assigned destination bank {destination_bank_id} is missing for {destination}"
                )
        for departure_utc in range(0, 1440, TIME_STEP_MINUTES):
            departure_local = _local_minute(departure_utc, origin, cities)
            arrival_utc = (departure_utc + block) % 1440
            arrival_local = _local_minute(arrival_utc, destination, cities)
            if origin in windows and not _inside_windows(
                departure_local, origin_windows
            ):
                continue
            if destination in windows and not _inside_windows(
                arrival_local, destination_windows
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
                    "originBankId": (
                        _bank_id(departure_local, windows[origin])
                        if origin in windows
                        else None
                    ),
                    "destinationBankId": (
                        _bank_id(arrival_local, windows[destination])
                        if destination in windows
                        else None
                    ),
                }
            )
            y_by_type[type_index].append(index)
            departures[(origin, departure_utc)].append(index)
            pairing_departures[(origin, destination)][departure_utc].append(index)
            arrivals[(destination, ready_utc)].append(index)
            station_events[origin].add(departure_utc)
            station_events[destination].add(ready_utc)
            if origin in windows:
                bank_touches[
                    (str(y_rows[index]["originBankId"]), "departure")
                ].append(index)
            if destination in windows:
                bank_touches[
                    (str(y_rows[index]["destinationBankId"]), "arrival")
                ].append(index)
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

    bank_capacity_constraints = 0
    if bank_touch_limits is not None:
        if bank_touch_constraint not in {"exact", "capacity"}:
            raise ValueError("Bank-touch constraints require exact or capacity mode")
        for hub_windows in windows.values():
            for window in hub_windows:
                for operation in ("arrival", "departure"):
                    key = (str(window["id"]), operation)
                    rows.append(
                        {index: 1.0 for index in bank_touches.get(key, [])}
                    )
                    limit = float(bank_touch_limits.get(key, 0))
                    lower_bounds.append(
                        limit if bank_touch_constraint == "exact" else 0.0
                    )
                    row_upper_bounds.append(limit)
                    bank_capacity_constraints += 1

    spacing_constraints = 0
    spacing_reserved_rejections = 0
    spacing_exception_variables = 0
    spacing_policy_exception_capacity = 0
    integer_auxiliary_variables: set[int] = set()
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
                    integer_auxiliary_variables.add(exception_index)
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
    integrality = np.zeros(len(objective))
    integrality[: len(y_rows)] = 1.0
    for station, events in station_events.items():
        integrality[q_by_event[(station, min(events))]] = 1.0
    for index in integer_auxiliary_variables:
        integrality[index] = 1.0
    result = milp(
        c=(
            np.zeros(len(objective))
            if feasibility_only
            else np.asarray(objective)
        ),
        integrality=integrality,
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
        "objectiveMode": "feasibility" if feasibility_only else "minimum_aircraft",
        **(
            {
                "bankCapacityConstraints": bank_capacity_constraints,
                "bankCapacityConstraintMode": bank_touch_constraint,
            }
            if bank_touch_limits is not None
            else {}
        ),
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

    plateau_random = random.Random(SUCCESSOR_PLATEAU_RANDOM_SEED)
    seen_states = {tuple(sorted(successors.items()))}
    aircraft_ceiling = _cycle_score(
        cycles, required_destinations, fleet_counts, rolling_limit
    )[-1]
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
        plateau_candidates = []
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
                    candidate_state = tuple(sorted(successors.items()))
                    successors[first], successors[second] = (
                        successors[second],
                        successors[first],
                    )
                    if (
                        candidate_score[-1] > aircraft_ceiling
                        or candidate_score > current_score
                    ):
                        continue
                    candidate = (
                        candidate_score,
                        first,
                        second,
                        candidate_cycles,
                        candidate_state,
                    )
                    if candidate_score == current_score:
                        if candidate_state not in seen_states:
                            plateau_candidates.append(candidate)
                        continue
                    if best is None or candidate_score < best[0]:
                        best = (
                            candidate_score,
                            first,
                            second,
                            candidate_cycles,
                            candidate_state,
                        )
        if best is None:
            if not plateau_candidates:
                break
            best = plateau_candidates[
                plateau_random.randrange(len(plateau_candidates))
            ]
            move_kind = "plateau"
        else:
            move_kind = "improvement"
        score, first, second, candidate_cycles, candidate_state = best
        successors[first], successors[second] = (
            successors[second],
            successors[first],
        )
        seen_states.add(candidate_state)
        swaps.append(
            {
                "firstArrivingLegId": first,
                "secondArrivingLegId": second,
                "moveKind": move_kind,
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
    seed_checkpoint_path: Path | None = None,
    seed_fleets_per_run: int | None = None,
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
    exact_options = planning_rules.get("exactMaterialization", {})
    enforce_fixed_inventory = bool(
        exact_options.get("enforceFixedPhysicalInventory", False)
    )
    if seed_fleets_per_run is not None:
        if seed_fleets_per_run < 1:
            raise ValueError("Seed fleets per run must be at least one")
        if seed_checkpoint_path is None:
            raise ValueError(
                "Seed fleets per run requires an exact seed checkpoint path"
            )
    bank_assignment_mode = exact_options.get(
        "bankAssignmentMode", "assigned_leg_waves"
    )
    joint_bank_assignment = (
        bank_assignment_mode == "joint_within_capacity_envelope"
    )
    profiles = {
        row["fleet"]: row
        for row in planning_rules["frequencyAllocation"]["fleetProfiles"]
    }
    inventory = _leg_inventory(frequency_plan, profiles, cities)
    if exact_options.get("preserveAssignedBankWaves", False):
        if joint_bank_assignment:
            raise ValueError(
                "Joint bank assignment cannot also preserve leg-level bank waves"
            )
        _apply_assigned_bank_waves(inventory, bank_plan)
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
    pairing_model = str(exact_options.get("pairingModel", "time_counts"))
    if pairing_model not in {"time_counts", "compiled_patterns"}:
        raise ValueError(f"Unsupported exact pairing model: {pairing_model}")
    if pairing_model == "compiled_patterns" and not enforce_pairing_spacing:
        raise ValueError(
            "Compiled pairing patterns require Section 2.6 spacing enforcement"
        )
    maximum_patterns = int(
        exact_options.get("maximumPatternsPerPairing", 96)
    )
    pairing_pattern_beam_width = int(
        exact_options.get("pairingPatternBeamWidth", 3000)
    )
    fleet_coordination = str(
        exact_options.get("fleetCoordination", "sequential")
    )
    if fleet_coordination not in {"sequential", "global"}:
        raise ValueError(
            f"Unsupported exact fleet coordination mode: {fleet_coordination}"
        )
    if fleet_coordination == "global" and (
        pairing_model != "compiled_patterns" or not joint_bank_assignment
    ):
        raise ValueError(
            "Global fleet coordination requires compiled patterns and joint bank assignment"
        )
    global_time_limit_seconds = int(
        exact_options.get(
            "globalTimeLimitSeconds",
            time_limit_seconds * len(fleet_counts),
        )
    )
    constructive_seed_mode = str(
        exact_options.get("constructiveSeed", "none")
    )
    if constructive_seed_mode not in {"none", "independent_fleets"}:
        raise ValueError(
            f"Unsupported constructive seed mode: {constructive_seed_mode}"
        )
    seed_time_limit_seconds = int(
        exact_options.get(
            "seedTimeLimitSecondsPerFleet", time_limit_seconds
        )
    )
    seed_time_limits_by_fleet = {
        str(fleet): int(seconds)
        for fleet, seconds in exact_options.get(
            "seedTimeLimitSecondsByFleet", {}
        ).items()
    }
    seed_pairing_model_by_fleet = {
        str(fleet): str(model)
        for fleet, model in exact_options.get(
            "seedPairingModelByFleet", {}
        ).items()
    }
    if any(
        model not in {"compiled_patterns", "time_counts"}
        for model in seed_pairing_model_by_fleet.values()
    ):
        raise ValueError(
            "Seed pairing models must be compiled_patterns or time_counts"
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
    bank_quotas_by_fleet: defaultdict[
        str, Counter[tuple[str, str]]
    ] = defaultdict(Counter)
    if joint_bank_assignment:
        for placement in bank_plan["placements"]:
            fleet = str(placement["fleet"])
            for touch in placement["bankTouches"]:
                bank_quotas_by_fleet[fleet][
                    (str(touch["bankId"]), str(touch["operation"]))
                ] += 1
    remaining_bank_capacity: dict[tuple[str, str], int] = {}
    if joint_bank_assignment:
        for hub in bank_plan["hubs"]:
            gate_count = _capacity(cities[str(hub["hub"])])[0]
            for bank in hub["banks"]:
                for operation in ("arrival", "departure"):
                    remaining_bank_capacity[
                        (str(bank["id"]), operation)
                    ] = gate_count

    materialized: dict[str, dict[str, Any]] = {}
    solver_fleets = {}
    joint_solver = None
    if fleet_coordination == "global":
        seed_materialized = None
        seed_solver_fleets: dict[str, dict[str, Any]] = {}
        seed_overflow: dict[tuple[str, str], int] = {}
        seed_physical_capacity_overflow: dict[tuple[str, int], int] = {}
        seed_passenger_gate_overflow: dict[tuple[str, int], int] = {}
        seed_reused_fleets: list[str] = []
        new_seed_fleets = 0
        if constructive_seed_mode == "independent_fleets":
            seed_materialized = {}
            seed_order = sorted(
                fleet_counts,
                key=lambda fleet: (
                    -len(inventory.get(fleet, [])),
                    fleet,
                ),
            )
            seed_materialized_by_fleet: dict[
                str, dict[str, dict[str, Any]]
            ] = {}
            seed_checkpoint_fingerprint = None
            if seed_checkpoint_path is not None:
                seed_checkpoint_fingerprint = _exact_seed_fingerprint(
                    canonical,
                    frequency_plan,
                    bank_plan,
                    repair_plan,
                    planning_rules,
                )
                (
                    seed_materialized_by_fleet,
                    seed_solver_fleets,
                ) = _read_exact_seed_checkpoint(
                    seed_checkpoint_path,
                    seed_checkpoint_fingerprint,
                    seed_order,
                )
                seed_reused_fleets = [
                    fleet
                    for fleet in seed_order
                    if fleet in seed_materialized_by_fleet
                ]
            for fleet in seed_order:
                if fleet in seed_materialized_by_fleet:
                    LOGGER.info("reusing exact seed fleet %s", fleet)
                    seed_materialized.update(
                        seed_materialized_by_fleet[fleet]
                    )
                    continue
                LOGGER.info("solving exact seed fleet %s", fleet)
                seed_started = time.monotonic()
                seed_pairing_model = seed_pairing_model_by_fleet.get(
                    fleet, "compiled_patterns"
                )
                fleet_time_limit = seed_time_limits_by_fleet.get(
                    fleet, seed_time_limit_seconds
                )
                if seed_pairing_model == "compiled_patterns":
                    fleet_legs, fleet_solver = (
                        _solve_fleet_with_pairing_patterns(
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
                            {},
                            remaining_bank_capacity,
                            "capacity",
                            True,
                            allow_pairing_spacing_exceptions,
                            fleet_time_limit,
                            maximum_patterns,
                            pairing_pattern_beam_width,
                        )
                    )
                else:
                    fleet_legs, fleet_solver = _solve_fleet(
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
                        {},
                        remaining_bank_capacity,
                        "capacity",
                        False,
                        True,
                        allow_pairing_spacing_exceptions,
                        fleet_time_limit,
                    )
                seed_materialized.update(fleet_legs)
                seed_materialized_by_fleet[fleet] = fleet_legs
                seed_solver_fleets[fleet] = fleet_solver
                LOGGER.info(
                    "completed exact seed fleet %s legs=%d in %.1fs",
                    fleet,
                    len(fleet_legs),
                    time.monotonic() - seed_started,
                )
                if (
                    seed_checkpoint_path is not None
                    and seed_checkpoint_fingerprint is not None
                ):
                    _write_exact_seed_checkpoint(
                        seed_checkpoint_path,
                        seed_checkpoint_fingerprint,
                        seed_order,
                        seed_materialized_by_fleet,
                        seed_solver_fleets,
                    )
                new_seed_fleets += 1
                if (
                    seed_fleets_per_run is not None
                    and new_seed_fleets >= seed_fleets_per_run
                ):
                    raise ExactSeedStageComplete(
                        [
                            fleet_name
                            for fleet_name in seed_order
                            if fleet_name in seed_materialized_by_fleet
                        ]
                    )
            seed_usage: Counter[tuple[str, str]] = Counter()
            for leg in seed_materialized.values():
                if leg["originBankId"] is not None:
                    seed_usage[
                        (str(leg["originBankId"]), "departure")
                    ] += 1
                if leg["destinationBankId"] is not None:
                    seed_usage[
                        (str(leg["destinationBankId"]), "arrival")
                    ] += 1
            seed_overflow = {
                key: touches - remaining_bank_capacity[key]
                for key, touches in seed_usage.items()
                if touches > remaining_bank_capacity[key]
            }
            seed_physical_capacity_overflow = (
                _materialized_physical_capacity_overflow(
                    seed_materialized,
                    cities,
                    int(policy["turns"]["minimumMinutes"]),
                )
            )
            if enforce_fixed_inventory:
                seed_passenger_gate_overflow = (
                    _materialized_passenger_gate_overflow(
                        seed_materialized,
                        cities,
                    )
                )
        if (
            seed_materialized is not None
            and not seed_overflow
            and not seed_physical_capacity_overflow
            and not seed_passenger_gate_overflow
        ):
            materialized = seed_materialized
            solver_fleets = seed_solver_fleets
            joint_solver = {
                "status": "constructive_seed_feasible",
                "message": (
                    "Checkpointed fleet solutions jointly satisfy the shared bank capacity"
                ),
                "bankFeasibilityOverflow": 0,
                "physicalCapacityFeasibilityOverflow": 0,
                "passengerGateFeasibilityOverflow": 0,
                "constructiveSeed": True,
                "seedCheckpointReusedFleets": seed_reused_fleets,
                "seedOverloadedBankRows": 0,
                "seedOverloadedPhysicalCapacityRows": 0,
                "seedOverloadedPassengerGateRows": 0,
                "timeLimitSeconds": global_time_limit_seconds,
            }
        else:
            materialized, solver_fleets, joint_solver = (
                _solve_all_fleets_with_pairing_patterns(
                    inventory,
                    {
                        fleet: int(count)
                        for fleet, count in fleet_counts.items()
                    },
                    {
                        fleet: sorted(assigned_by_fleet[fleet])
                        for fleet in fleet_counts
                    },
                    cities,
                    policy,
                    windows,
                    targets,
                    pairing_departure_counts,
                    station_departure_counts,
                    remaining_bank_capacity,
                    allow_pairing_spacing_exceptions,
                    global_time_limit_seconds,
                    maximum_patterns,
                    pairing_pattern_beam_width,
                    seed_materialized,
                    enforce_fixed_inventory,
                )
            )
            if joint_solver is not None:
                joint_solver["seedTotalBankOverage"] = sum(
                    seed_overflow.values()
                )
                joint_solver["seedTotalPhysicalCapacityOverage"] = sum(
                    seed_physical_capacity_overflow.values()
                )
                joint_solver["seedTotalPassengerGateOverage"] = sum(
                    seed_passenger_gate_overflow.values()
                )
                joint_solver["seedCheckpointReusedFleets"] = (
                    seed_reused_fleets
                )
                if seed_checkpoint_path is not None:
                    repair_seed_order = sorted(
                        fleet_counts,
                        key=lambda fleet: (
                            -len(inventory.get(fleet, [])),
                            fleet,
                        ),
                    )
                    improved_by_fleet: dict[
                        str, dict[str, dict[str, Any]]
                    ] = {fleet: {} for fleet in repair_seed_order}
                    for leg_id, leg in materialized.items():
                        improved_by_fleet[str(leg["fleet"])][leg_id] = leg
                    _write_exact_seed_checkpoint(
                        seed_checkpoint_path,
                        _exact_seed_fingerprint(
                            canonical,
                            frequency_plan,
                            bank_plan,
                            repair_plan,
                            planning_rules,
                        ),
                        repair_seed_order,
                        improved_by_fleet,
                        solver_fleets,
                    )
                if (
                    float(joint_solver["bankFeasibilityOverflow"]) > 0
                    or float(
                        joint_solver[
                            "physicalCapacityFeasibilityOverflow"
                        ]
                    )
                    > 0
                    or float(
                        joint_solver[
                            "passengerGateFeasibilityOverflow"
                        ]
                    )
                    > 0
                ):
                    raise ExactGlobalRepairIncomplete(
                        {
                            str(key): float(value)
                            for key, value in joint_solver[
                                "bankOverflowRows"
                            ].items()
                        },
                        str(joint_solver["message"]),
                        {
                            str(key): float(value)
                            for key, value in joint_solver[
                                "physicalCapacityOverflowRows"
                            ].items()
                        },
                        {
                            str(key): float(value)
                            for key, value in joint_solver[
                                "passengerGateOverflowRows"
                            ].items()
                        },
                    )
        for leg in materialized.values():
            if leg["originBankId"] is not None:
                remaining_bank_capacity[
                    (str(leg["originBankId"]), "departure")
                ] -= 1
            if leg["destinationBankId"] is not None:
                remaining_bank_capacity[
                    (str(leg["destinationBankId"]), "arrival")
                ] -= 1
        if min(remaining_bank_capacity.values(), default=0) < 0:
            raise ValueError("Exact global materialization exceeded bank capacity")
    else:
        configured_fleet_order = exact_options.get("fleetSolveOrder")
        if configured_fleet_order is not None:
            fleet_order = [str(fleet) for fleet in configured_fleet_order]
            if set(fleet_order) != set(fleet_counts) or len(fleet_order) != len(
                fleet_counts
            ):
                raise ValueError(
                    "Exact fleetSolveOrder must list every configured fleet exactly once"
                )
        else:
            fleet_order = (
                sorted(
                    fleet_counts,
                    key=lambda fleet: (-len(inventory.get(fleet, [])), fleet),
                )
                if joint_bank_assignment
                else list(fleet_counts)
            )
        for fleet_position, fleet in enumerate(fleet_order):
            bank_limits = None
            if joint_bank_assignment:
                future_fleets = fleet_order[fleet_position + 1 :]
                bank_limits = {
                    key: max(
                        0,
                        remaining
                        - sum(
                            int(bank_quotas_by_fleet[future][key])
                            for future in future_fleets
                        ),
                    )
                    for key, remaining in remaining_bank_capacity.items()
                }
            if pairing_model == "compiled_patterns":
                fleet_legs, solver = _solve_fleet_with_pairing_patterns(
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
                    bank_limits,
                    "capacity" if joint_bank_assignment else None,
                    joint_bank_assignment,
                    allow_pairing_spacing_exceptions,
                    time_limit_seconds,
                    maximum_patterns,
                    pairing_pattern_beam_width,
                )
            else:
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
                    bank_limits,
                    "capacity" if joint_bank_assignment else None,
                    joint_bank_assignment,
                    enforce_pairing_spacing,
                    allow_pairing_spacing_exceptions,
                    time_limit_seconds,
                )
            materialized.update(fleet_legs)
            solver_fleets[fleet] = solver
            if joint_bank_assignment:
                for leg in fleet_legs.values():
                    if leg["originBankId"] is not None:
                        key = (str(leg["originBankId"]), "departure")
                        remaining_bank_capacity[key] -= 1
                    if leg["destinationBankId"] is not None:
                        key = (str(leg["destinationBankId"]), "arrival")
                        remaining_bank_capacity[key] -= 1
                if min(remaining_bank_capacity.values(), default=0) < 0:
                    raise ValueError(
                        f"Exact {fleet} materialization exceeded bank capacity"
                    )
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
    gate_diagnostic = {
        "status": "not_evaluated",
        "stations": 0,
        "towMovements": 0,
        "failures": [],
    }
    if enforce_fixed_inventory:
        _, gate_diagnostic = _materialized_gate_assignments(
            materialized,
            successors,
            cities,
            minimum_turn,
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
    if enforce_fixed_inventory:
        checks.append(
            {
                "id": "fixed_physical_inventory",
                "status": gate_diagnostic["status"],
                "hardStop": True,
                "message": (
                    f"All {gate_diagnostic['stations']} stations fit their configured gates and stands with {gate_diagnostic['towMovements']} conditional tow(s)"
                    if gate_diagnostic["status"] == "pass"
                    else f"{len(gate_diagnostic['failures'])} stations cannot fit their configured gates and stands"
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
                {
                    "gateCapacityFailures": len(
                        gate_diagnostic["failures"]
                    ),
                    "conditionalTows": int(
                        gate_diagnostic["towMovements"]
                    ),
                }
                if enforce_fixed_inventory
                else {}
            ),
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
            "fleetCoordination": fleet_coordination,
            "fleets": solver_fleets,
            **(
                {
                    "globalTimeLimitSeconds": global_time_limit_seconds,
                    "joint": joint_solver,
                }
                if joint_solver is not None
                else {}
            ),
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
                {"gateCapacity": gate_diagnostic}
                if enforce_fixed_inventory
                else {}
            ),
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
            (
                "Exact-cycle gate and stand claims use fixed physical inventory; RON/ROD towing is conditional and passenger handling remains at gates."
                if enforce_fixed_inventory
                else "Gate and stand capacity has not yet been evaluated against these newly materialized cycles."
            ),
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
    seed_checkpoint_path: Path | None = None,
    seed_fleets_per_run: int | None = None,
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
        seed_checkpoint_path,
        seed_fleets_per_run,
    )
