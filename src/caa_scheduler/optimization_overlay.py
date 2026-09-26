from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any


def _clock(minute: int) -> str:
    return f"{(minute // 60) % 24:02}:{minute % 60:02}"


def apply_optimization_overlay(
    canonical: dict[str, Any], overlay: dict[str, Any]
) -> dict[str, Any]:
    """Apply an auditable, schedule-specific feasibility overlay.

    The overlay is intentionally narrower than the construction optimizer. It
    may retime named legs and insert named legs into existing routes, but it
    cannot remove a leg, change fleet counts, or synthesize a route. The output
    remains a draft feasibility checkpoint until the normal construction and
    packaging stages regenerate final provenance.
    """

    expected_base = overlay["baseSchedule"]["scheduleId"]
    actual_base = canonical["schedule"]["id"]
    if actual_base != expected_base:
        raise ValueError(
            f"Overlay expects base schedule {expected_base}, received {actual_base}"
        )

    result = copy.deepcopy(canonical)
    result["schedule"].update(copy.deepcopy(overlay["schedule"]))
    result["gatePlan"]["label"] = result["schedule"]["label"]

    existing_bank_ids = {bank["id"] for bank in result.get("hubBanks", [])}
    for bank in overlay.get("hubBanksToAdd", []):
        if bank["id"] in existing_bank_ids:
            raise ValueError(f"Overlay bank already exists: {bank['id']}")
        result.setdefault("hubBanks", []).append(copy.deepcopy(bank))
        existing_bank_ids.add(bank["id"])

    for hub, count in overlay.get("hubBankCountOverrides", {}).items():
        result["operatingPolicy"]["hubBankCounts"][hub] = count

    existing_overrides = {
        (item["checkId"], item["findingId"])
        for item in result["operatingPolicy"].get("overrides", [])
    }
    for item in overlay.get("operatingOverrides", []):
        key = (item["checkId"], item["findingId"])
        if key in existing_overrides:
            raise ValueError(f"Duplicate operating override: {key[0]}:{key[1]}")
        result["operatingPolicy"].setdefault("overrides", []).append(
            copy.deepcopy(item)
        )
        existing_overrides.add(key)

    legs_by_id = {leg["id"]: leg for leg in result["legs"]}
    touched_routes: set[int] = set()
    for change in overlay.get("retimeLegs", []):
        leg = legs_by_id.get(change["legId"])
        if leg is None:
            raise ValueError(f"Cannot retime missing leg {change['legId']}")
        for field in ("departureMinute", "arrivalMinute"):
            expected_key = f"expected{field[0].upper()}{field[1:]}"
            if expected_key in change and leg[field] != change[expected_key]:
                raise ValueError(
                    f"Stale overlay for {change['legId']}: expected {field} "
                    f"{change[expected_key]}, found {leg[field]}"
                )
            leg[field] = int(change[field])
        leg["departure"] = _clock(leg["departureMinute"])
        leg["arrival"] = _clock(leg["arrivalMinute"])
        touched_routes.add(int(leg["route"]))

    route_attributes: defaultdict[int, set[tuple[str, str, int]]] = defaultdict(set)
    for leg in result["legs"]:
        route_attributes[int(leg["route"])].add(
            (str(leg["line"]), str(leg["fleet"]), int(leg["day"]))
        )

    directed_pairings: dict[tuple[str, str], int] = {}
    for leg in result["legs"]:
        directed_pairings.setdefault(
            (str(leg["origin"]), str(leg["destination"])), int(leg["pairing"])
        )
    next_pairing = max(int(leg["pairing"]) for leg in result["legs"]) + 1
    next_flight = max(int(leg["flight"]) for leg in result["legs"]) + 1

    line_days = {
        (str(leg["line"]), int(leg["day"])) for leg in result["legs"]
    }
    existing_routes = {int(leg["route"]) for leg in result["legs"]}
    for addition in overlay.get("addRoutes", []):
        route = int(addition["route"])
        line = str(addition["line"])
        day = int(addition["day"])
        fleet = str(addition["fleet"])
        if route in existing_routes:
            raise ValueError(f"Overlay route already exists: {route}")
        if (line, day) in line_days:
            raise ValueError(f"Overlay line/day already exists: {line}-{day}")
        if fleet not in result["schedule"]["fleetCounts"]:
            raise ValueError(f"Overlay route {route} uses unknown fleet {fleet}")
        route_legs = addition.get("legs", [])
        if not route_legs:
            raise ValueError(f"Overlay route {route} has no legs")

        previous_destination: str | None = None
        for sequence, item in enumerate(route_legs, start=1):
            identifier = str(item["id"])
            if identifier in legs_by_id:
                raise ValueError(f"Overlay leg already exists: {identifier}")
            origin = str(item["origin"])
            destination = str(item["destination"])
            if previous_destination is not None and origin != previous_destination:
                raise ValueError(
                    f"Overlay route {route} is discontinuous before {identifier}: "
                    f"expected {previous_destination}, found {origin}"
                )
            market = (origin, destination)
            pairing = directed_pairings.get(market)
            if pairing is None:
                pairing = next_pairing
                next_pairing += 1
                directed_pairings[market] = pairing
            departure = int(item["departureMinute"])
            arrival = int(item["arrivalMinute"])
            leg = {
                "id": identifier,
                "route": route,
                "line": line,
                "fleet": fleet,
                "day": day,
                "sequenceWithinRoute": sequence,
                "pairing": pairing,
                "flight": next_flight,
                "origin": origin,
                "destination": destination,
                "departure": _clock(departure),
                "arrival": _clock(arrival),
                "departureMinute": departure,
                "arrivalMinute": arrival,
            }
            next_flight += 1
            result["legs"].append(leg)
            legs_by_id[identifier] = leg
            previous_destination = destination

        route_attributes[route].add((line, fleet, day))
        existing_routes.add(route)
        line_days.add((line, day))
        touched_routes.add(route)

    for addition in overlay.get("insertLegs", []):
        identifier = addition["id"]
        if identifier in legs_by_id:
            raise ValueError(f"Overlay leg already exists: {identifier}")
        route = int(addition["route"])
        attributes = route_attributes.get(route, set())
        if len(attributes) != 1:
            raise ValueError(
                f"Inserted leg {identifier} needs one existing route identity for {route}"
            )
        line, fleet, day = next(iter(attributes))
        market = (str(addition["origin"]), str(addition["destination"]))
        pairing = directed_pairings.get(market)
        if pairing is None:
            pairing = next_pairing
            next_pairing += 1
            directed_pairings[market] = pairing
        departure = int(addition["departureMinute"])
        arrival = int(addition["arrivalMinute"])
        leg = {
            "id": identifier,
            "route": route,
            "line": line,
            "fleet": fleet,
            "day": day,
            "sequenceWithinRoute": 0,
            "pairing": pairing,
            "flight": next_flight,
            "origin": market[0],
            "destination": market[1],
            "departure": _clock(departure),
            "arrival": _clock(arrival),
            "departureMinute": departure,
            "arrivalMinute": arrival,
        }
        next_flight += 1
        result["legs"].append(leg)
        legs_by_id[identifier] = leg
        touched_routes.add(route)

    for route in touched_routes:
        route_legs = [leg for leg in result["legs"] if int(leg["route"]) == route]
        route_legs.sort(
            key=lambda leg: (
                int(leg["departureMinute"])
                if int(leg["departureMinute"]) >= 180
                else int(leg["departureMinute"]) + 1440
            )
        )
        for sequence, leg in enumerate(route_legs, start=1):
            leg["sequenceWithinRoute"] = sequence

    for replacement in overlay.get("bankAssignmentReplacements", []):
        matches = [
            item
            for item in result.get("bankAssignments", [])
            if item["legId"] == replacement["legId"]
            and item["operation"] == replacement["operation"]
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one bank assignment for {replacement['legId']} "
                f"{replacement['operation']}, found {len(matches)}"
            )
        matches[0]["bankId"] = replacement["bankId"]

    result.setdefault("bankAssignments", []).extend(
        copy.deepcopy(overlay.get("bankAssignmentsToAdd", []))
    )
    return result
