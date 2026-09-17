from __future__ import annotations

from collections import defaultdict
from typing import Any, NamedTuple


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


def build_claims(legs: list[dict[str, Any]], city_code: str) -> list[GateClaim]:
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
                    claims.append(
                        GateClaim(
                            leg["arrivalMinute"],
                            next_leg["departureMinute"],
                            str(route),
                            fleet,
                            "turn",
                            leg["origin"],
                            next_leg["destination"],
                        )
                    )
                    continue

                next_day = day + 1 if day + 1 <= max_day else 1
                next_day_legs = days.get(next_day, [])
                if next_day_legs and next_day_legs[0]["origin"] == city_code:
                    next_route = next_day_legs[0]["route"]
                    claims.append(
                        GateClaim(
                            leg["arrivalMinute"],
                            next_day_legs[0]["departureMinute"] + 1440,
                            f"{route} -> {next_route}",
                            fleet,
                            "ron",
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

    result = list(assignment.items())
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
