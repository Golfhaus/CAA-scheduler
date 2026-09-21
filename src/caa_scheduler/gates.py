from __future__ import annotations

from collections import defaultdict
from typing import Any, NamedTuple

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


TOUCH_ARRIVAL_MINUTES = 45
TOUCH_DEPARTURE_MINUTES = 60
SHORT_CLAIM_THRESHOLD_MINUTES = 150


class GateClaim(NamedTuple):
    start: int | float
    end: int | float
    label: str
    fleet: str
    kind: str
    arrival_city: str | None
    departure_city: str | None


Assignment = tuple[GateClaim, int]


class GateCapacityError(ValueError):
    """Raised when claims cannot fit the configured physical inventory."""

    def __init__(
        self,
        message: str,
        *,
        required_gates: int,
        configured_gates: int,
        required_stands: int,
        configured_stands: int,
        stranded_touches: list[GateClaim] | None = None,
    ) -> None:
        super().__init__(message)
        self.required_gates = required_gates
        self.configured_gates = configured_gates
        self.required_stands = required_stands
        self.configured_stands = configured_stands
        self.stranded_touches = stranded_touches or []


def build_claims(
    legs: list[dict[str, Any]],
    city_code: str,
    *,
    cyclic_successor_holds: bool = False,
) -> list[GateClaim]:
    """Build recurring turn, overnight, origin, and termination claims.

    This is the single authoritative implementation used by validators and
    exporters. It preserves the two-pass wraparound handling proven against
    Schedule 6: all arrival-side claims for a line are built before duplicate
    origin-only claims are considered.
    """
    lines: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(dict)
    for leg in legs:
        lines[leg["line"]].setdefault(leg["day"], []).append(leg)
    for days in lines.values():
        for day_legs in days.values():
            day_legs.sort(key=lambda item: item["departureMinute"])

    claims: list[GateClaim] = []
    for days in lines.values():
        max_day = max(days)
        sorted_days = sorted(days)

        for day in sorted_days:
            day_legs = days[day]
            route = day_legs[0]["route"]
            fleet = day_legs[0]["fleet"]
            for index, leg in enumerate(day_legs):
                if leg["destination"] != city_code:
                    continue
                next_leg = next(
                    (
                        candidate
                        for candidate in day_legs[index + 1 :]
                        if candidate["origin"] == city_code
                    ),
                    None,
                )
                if next_leg is not None:
                    end = next_leg["departureMinute"]
                    kind = "turn"
                    if cyclic_successor_holds:
                        wait = (
                            int(next_leg["departureMinute"])
                            - int(leg["arrivalMinute"])
                        ) % 1440
                        if wait == 0:
                            wait = 1440
                        end = int(leg["arrivalMinute"]) + wait
                        kind = "ron" if wait >= 360 else "turn"
                    claims.append(
                        GateClaim(
                            leg["arrivalMinute"],
                            end,
                            str(route),
                            fleet,
                            kind,
                            leg["origin"],
                            next_leg["destination"],
                        )
                    )
                    continue

                next_day = day + 1 if day + 1 <= max_day else 1
                next_day_legs = days.get(next_day, [])
                if next_day_legs and next_day_legs[0]["origin"] == city_code:
                    next_route = next_day_legs[0]["route"]
                    end = next_day_legs[0]["departureMinute"] + 1440
                    kind = "ron"
                    if cyclic_successor_holds:
                        wait = (
                            int(next_day_legs[0]["departureMinute"])
                            - int(leg["arrivalMinute"])
                        ) % 1440
                        if wait == 0:
                            wait = 1440
                        end = int(leg["arrivalMinute"]) + wait
                        kind = "ron" if wait >= 360 else "turn"
                    claims.append(
                        GateClaim(
                            leg["arrivalMinute"],
                            end,
                            f"{route} -> {next_route}",
                            fleet,
                            kind,
                            leg["origin"],
                            next_day_legs[0]["destination"],
                        )
                    )
                else:
                    claims.append(
                        GateClaim(
                            leg["arrivalMinute"],
                            leg["arrivalMinute"] + TOUCH_ARRIVAL_MINUTES,
                            str(route),
                            fleet,
                            "terminate_only",
                            leg["origin"],
                            None,
                        )
                    )

        for day in sorted_days:
            day_legs = days[day]
            route = day_legs[0]["route"]
            fleet = day_legs[0]["fleet"]
            first_leg = day_legs[0]
            if first_leg["origin"] != city_code:
                continue
            already_covered = any(
                (
                    claim.label == str(route)
                    or claim.label.endswith(f" -> {route}")
                )
                and abs(
                    (claim.end - first_leg["departureMinute"]) % 1440
                )
                < 0.5
                for claim in claims
            )
            if not already_covered:
                claims.append(
                    GateClaim(
                        first_leg["departureMinute"]
                        - TOUCH_DEPARTURE_MINUTES,
                        first_leg["departureMinute"],
                        str(route),
                        fleet,
                        "originate_only",
                        None,
                        first_leg["destination"],
                    )
                )
    return claims


def overlaps(first: GateClaim, second: GateClaim) -> bool:
    """Return whether two daily recurring claims overlap cyclically."""
    for first_shift in (-1440, 0, 1440):
        for second_shift in (-1440, 0, 1440):
            if (
                first.start + first_shift < second.end + second_shift
                and second.start + second_shift < first.end + first_shift
            ):
                return True
    return False


def _conflict_graph(claims: list[GateClaim]) -> list[set[int]]:
    adjacency = [set() for _ in claims]
    for first in range(len(claims)):
        for second in range(first + 1, len(claims)):
            if overlaps(claims[first], claims[second]):
                adjacency[first].add(second)
                adjacency[second].add(first)
    return adjacency


def _greedy_coloring(claims: list[GateClaim]) -> list[int]:
    """Color a cyclic interval-conflict graph with deterministic DSATUR."""
    if not claims:
        return []
    adjacency = _conflict_graph(claims)
    colors = [0] * len(claims)
    for _ in claims:
        uncolored = [index for index, color in enumerate(colors) if not color]
        vertex = max(
            uncolored,
            key=lambda index: (
                len({colors[neighbor] for neighbor in adjacency[index] if colors[neighbor]}),
                len(adjacency[index]),
                -index,
            ),
        )
        unavailable = {
            colors[neighbor]
            for neighbor in adjacency[vertex]
            if colors[neighbor]
        }
        color = next(
            candidate
            for candidate in range(1, len(claims) + 1)
            if candidate not in unavailable
        )
        colors[vertex] = color
    return colors


def _bounded_coloring(
    claims: list[GateClaim], maximum_slots: int
) -> list[int] | None:
    colors = _greedy_coloring(claims)
    if max(colors, default=0) <= maximum_slots:
        return colors
    if maximum_slots < 1:
        return None

    adjacency = _conflict_graph(claims)
    variable_count = len(claims) * maximum_slots
    row_indexes: list[int] = []
    column_indexes: list[int] = []
    values: list[float] = []
    lower_bounds: list[float] = []
    upper_bounds: list[float] = []

    for claim_index in range(len(claims)):
        row = len(lower_bounds)
        for color in range(maximum_slots):
            row_indexes.append(row)
            column_indexes.append(claim_index * maximum_slots + color)
            values.append(1.0)
        lower_bounds.append(1.0)
        upper_bounds.append(1.0)

    for first, neighbors in enumerate(adjacency):
        for second in sorted(neighbor for neighbor in neighbors if neighbor > first):
            for color in range(maximum_slots):
                row = len(lower_bounds)
                row_indexes.extend((row, row))
                column_indexes.extend(
                    (
                        first * maximum_slots + color,
                        second * maximum_slots + color,
                    )
                )
                values.extend((1.0, 1.0))
                lower_bounds.append(-np.inf)
                upper_bounds.append(1.0)

    matrix = coo_matrix(
        (values, (row_indexes, column_indexes)),
        shape=(len(lower_bounds), variable_count),
    ).tocsr()
    result = milp(
        c=np.zeros(variable_count),
        integrality=np.ones(variable_count),
        bounds=Bounds(np.zeros(variable_count), np.ones(variable_count)),
        constraints=LinearConstraint(
            matrix,
            np.asarray(lower_bounds),
            np.asarray(upper_bounds),
        ),
        options={"time_limit": 30},
    )
    if result.x is None:
        return None
    return [
        max(
            range(maximum_slots),
            key=lambda color: result.x[claim_index * maximum_slots + color],
        )
        + 1
        for claim_index in range(len(claims))
    ]


def split_for_waypoint(
    claim: GateClaim,
) -> tuple[GateClaim, GateClaim, GateClaim]:
    shared = (
        claim.label,
        claim.fleet,
        claim.kind,
        claim.arrival_city,
        claim.departure_city,
    )
    gate_in = GateClaim(
        claim.start,
        claim.start + TOUCH_ARRIVAL_MINUTES,
        *shared,
    )
    stand_middle = GateClaim(
        claim.start + TOUCH_ARRIVAL_MINUTES,
        claim.end - TOUCH_DEPARTURE_MINUTES,
        *shared,
    )
    gate_out = GateClaim(
        claim.end - TOUCH_DEPARTURE_MINUTES,
        claim.end,
        *shared,
    )
    return gate_in, stand_middle, gate_out


def apply_forced_stand_splits(
    claims: list[GateClaim], force_labels: set[str]
) -> list[GateClaim]:
    result: list[GateClaim] = []
    for claim in claims:
        if claim.label not in force_labels:
            result.append(claim)
            continue
        gate_in, stand_middle, gate_out = split_for_waypoint(claim)
        stand_middle = stand_middle._replace(kind="forced_stand_mid")
        result.extend((gate_in, stand_middle, gate_out))
    return result


def assign_gates(
    claims: list[GateClaim],
    n_gates: int | None = None,
    *,
    n_stands: int | None = None,
    return_provenance: bool = False,
) -> list[Assignment] | tuple[list[Assignment], set[GateClaim]]:
    """Assign claims using short-first packing and targeted long-hold rescue.

    Long claims are split only when they can rescue a short claim or when a
    long claim would otherwise sit directly on a stand. Provenance protects
    deliberate stand-middle pieces from recursive splitting or compaction.
    """
    sorted_claims = sorted(
        claims,
        key=lambda claim: (
            0
            if claim.end - claim.start <= SHORT_CLAIM_THRESHOLD_MINUTES
            else 1,
            claim.start,
        ),
    )
    slots: defaultdict[int, list[GateClaim]] = defaultdict(list)
    assignment: dict[GateClaim, int] = {}
    for claim in sorted_claims:
        slot = (
            n_gates + 1
            if claim.kind == "forced_stand_mid" and n_gates is not None
            else 1
        )
        while not all(not overlaps(claim, existing) for existing in slots[slot]):
            slot += 1
        slots[slot].append(claim)
        assignment[claim] = slot

    if n_gates is None:
        if n_stands is not None:
            raise ValueError("Configured stands require a configured gate count")
        result = list(assignment.items())
        return (result, set()) if return_provenance else result

    stand_middles = {
        claim for claim in sorted_claims if claim.kind == "forced_stand_mid"
    }

    def place_touch(piece: GateClaim, preferred_slot: int, short: GateClaim) -> None:
        def slot_is_available(slot: int) -> bool:
            return not (
                slot == preferred_slot and overlaps(piece, short)
            ) and not any(overlaps(piece, existing) for existing in slots[slot])

        if overlaps(piece, short) or any(
            overlaps(piece, existing)
            for existing in slots[preferred_slot]
            if existing is not short
        ):
            piece_slot = 1
            while piece_slot <= n_gates and not slot_is_available(piece_slot):
                piece_slot += 1
            if piece_slot > n_gates:
                piece_slot = n_gates + 1
                while not slot_is_available(piece_slot):
                    piece_slot += 1
        else:
            piece_slot = preferred_slot
        slots[piece_slot].append(piece)
        assignment[piece] = piece_slot

    def try_rescue(short: GateClaim) -> bool:
        for slot in list(slots):
            if slot == assignment[short]:
                continue
            blockers = [
                existing for existing in slots[slot] if overlaps(short, existing)
            ]
            if len(blockers) != 1:
                continue
            blocker = blockers[0]
            if (
                blocker.end - blocker.start <= SHORT_CLAIM_THRESHOLD_MINUTES
                or blocker in stand_middles
            ):
                continue

            slots[slot].remove(blocker)
            del assignment[blocker]
            gate_in, stand_middle, gate_out = split_for_waypoint(blocker)
            place_touch(gate_in, slot, short)
            place_touch(gate_out, slot, short)

            old_slot = assignment[short]
            slots[old_slot].remove(short)
            slots[slot].append(short)
            assignment[short] = slot

            stand_slot = n_gates + 1
            while any(
                overlaps(stand_middle, existing) for existing in slots[stand_slot]
            ):
                stand_slot += 1
            slots[stand_slot].append(stand_middle)
            assignment[stand_middle] = stand_slot
            stand_middles.add(stand_middle)
            return True
        return False

    overflowed_short = [
        claim
        for claim in claims
        if assignment[claim] > n_gates
        and claim.end - claim.start <= SHORT_CLAIM_THRESHOLD_MINUTES
    ]
    for claim in overflowed_short:
        try_rescue(claim)

    long_on_stand = sorted(
        (
            claim
            for claim in list(assignment)
            if claim.end - claim.start > SHORT_CLAIM_THRESHOLD_MINUTES
            and assignment[claim] > n_gates
            and claim not in stand_middles
        ),
        key=lambda claim: claim.start,
    )
    for claim in long_on_stand:
        old_slot = assignment[claim]
        slots[old_slot].remove(claim)
        del assignment[claim]
        gate_in, stand_middle, gate_out = split_for_waypoint(claim)
        for piece in (gate_in, gate_out):
            piece_slot = 1
            while piece_slot <= n_gates and any(
                overlaps(piece, existing) for existing in slots[piece_slot]
            ):
                piece_slot += 1
            if piece_slot > n_gates:
                piece_slot = n_gates + 1
                while any(
                    overlaps(piece, existing) for existing in slots[piece_slot]
                ):
                    piece_slot += 1
            slots[piece_slot].append(piece)
            assignment[piece] = piece_slot

        stand_slot = n_gates + 1
        while any(
            overlaps(stand_middle, existing) for existing in slots[stand_slot]
        ):
            stand_slot += 1
        slots[stand_slot].append(stand_middle)
        assignment[stand_middle] = stand_slot
        stand_middles.add(stand_middle)

    stranded_touches = [
        claim
        for claim in list(assignment)
        if assignment[claim] > n_gates
        and claim.end - claim.start <= SHORT_CLAIM_THRESHOLD_MINUTES
        and claim not in stand_middles
    ]
    for claim in sorted(stranded_touches, key=lambda item: item.start):
        current_slot = assignment[claim]
        for slot in range(1, n_gates + 1):
            if not any(overlaps(claim, existing) for existing in slots[slot]):
                slots[current_slot].remove(claim)
                slots[slot].append(claim)
                assignment[claim] = slot
                break

    if n_stands is not None:
        while True:
            gate_claims = [
                claim for claim in assignment if claim not in stand_middles
            ]
            stand_claims = [
                claim for claim in assignment if claim in stand_middles
            ]
            if (
                _bounded_coloring(gate_claims, n_gates) is not None
                and _bounded_coloring(stand_claims, n_stands) is not None
            ):
                break
            towable = [
                claim
                for claim in gate_claims
                if claim.end - claim.start > SHORT_CLAIM_THRESHOLD_MINUTES
            ]
            trials = []
            for claim in towable:
                gate_in, stand_middle, gate_out = split_for_waypoint(claim)
                trial_gate_claims = [
                    candidate
                    for candidate in gate_claims
                    if candidate is not claim
                ] + [gate_in, gate_out]
                trial_stand_claims = stand_claims + [stand_middle]
                gate_colors = _greedy_coloring(trial_gate_claims)
                stand_colors = _greedy_coloring(trial_stand_claims)
                required_stands = max(stand_colors, default=0)
                if required_stands > n_stands:
                    continue
                trials.append(
                    (
                        max(gate_colors, default=0),
                        required_stands,
                        claim.start,
                        claim,
                        gate_in,
                        stand_middle,
                        gate_out,
                    )
                )
            if not trials:
                break
            (
                _,
                _,
                _,
                claim,
                gate_in,
                stand_middle,
                gate_out,
            ) = min(trials, key=lambda trial: trial[:3])
            del assignment[claim]
            assignment[gate_in] = 0
            assignment[gate_out] = 0
            assignment[stand_middle] = 0
            stand_middles.add(stand_middle)

        gate_claims = [
            claim for claim in assignment if claim not in stand_middles
        ]
        gate_colors = _bounded_coloring(gate_claims, n_gates)
        if gate_colors is not None:
            for claim, color in zip(gate_claims, gate_colors):
                assignment[claim] = color
        stand_claims = [
            claim for claim in assignment if claim in stand_middles
        ]
        stand_colors = _bounded_coloring(stand_claims, n_stands)
        if stand_colors is not None:
            for claim, color in zip(stand_claims, stand_colors):
                assignment[claim] = n_gates + color

    result = list(assignment.items())
    if n_stands is not None:
        stranded_touches = [
            claim
            for claim, slot in result
            if slot > n_gates and claim not in stand_middles
        ]
        required_stands = max(
            (slot - n_gates for _, slot in result if slot > n_gates),
            default=0,
        )
        if stranded_touches or required_stands > n_stands:
            required_gates = max(
                n_gates + (1 if stranded_touches else 0),
                max((slot for _, slot in result if slot <= n_gates), default=0),
            )
            problems = []
            if stranded_touches:
                problems.append(
                    f"{len(stranded_touches)} passenger touch(es) remain off-gate"
                )
            if required_stands > n_stands:
                problems.append(
                    f"stand {required_stands} is required but only {n_stands} are configured"
                )
            raise GateCapacityError(
                "; ".join(problems),
                required_gates=required_gates,
                configured_gates=n_gates,
                required_stands=required_stands,
                configured_stands=n_stands,
                stranded_touches=stranded_touches,
            )
    return (result, stand_middles) if return_provenance else result


def serialize_assignments(
    assignments: list[Assignment], n_gates: int
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for claim, slot in assignments:
        row_type = "gate" if slot <= n_gates else "stand"
        row = slot if slot <= n_gates else slot - n_gates
        claims.append(
            {
                "start": claim.start,
                "end": claim.end,
                "label": claim.label,
                "fleet": claim.fleet,
                "kind": claim.kind,
                "row": row,
                "rowType": row_type,
                "arrivalCity": claim.arrival_city,
                "departureCity": claim.departure_city,
            }
        )
    claims.sort(key=lambda claim: claim["start"])

    by_label: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        by_label[claim["label"]].append(claim)
    for pieces in by_label.values():
        ordered_pieces = sorted(pieces, key=lambda claim: claim["start"])
        for first, second in zip(ordered_pieces, ordered_pieces[1:]):
            if first["end"] == second["start"] and (
                first["row"],
                first["rowType"],
            ) != (second["row"], second["rowType"]):
                first["moveTo"] = {
                    "row": second["row"],
                    "rowType": second["rowType"],
                }
                second["moveFrom"] = {
                    "row": first["row"],
                    "rowType": first["rowType"],
                }
    return claims


def peak_demand(claims: list[GateClaim]) -> int:
    return max(
        (
            sum(
                1
                for claim in claims
                if overlaps(
                    claim,
                    GateClaim(minute, minute + 1, "", "", "", None, None),
                )
            )
            for minute in range(0, 1440, 15)
        ),
        default=0,
    )
