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
    may retime, replace, and insert named legs and may re-close existing route
    cycles without changing fleet counts. The output remains a draft
    feasibility checkpoint until the normal construction and packaging stages
    regenerate final provenance.
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

    banks_by_id = {bank["id"]: bank for bank in result.get("hubBanks", [])}
    for change in overlay.get("hubBankChanges", []):
        bank = banks_by_id.get(change["bankId"])
        if bank is None:
            raise ValueError(f"Cannot change missing hub bank {change['bankId']}")
        for field in ("startMinute", "endMinute"):
            expected_key = f"expected{field[0].upper()}{field[1:]}"
            if expected_key in change and bank[field] != change[expected_key]:
                raise ValueError(
                    f"Stale overlay for {change['bankId']}: expected {field} "
                    f"{change[expected_key]}, found {bank[field]}"
                )
            if field in change:
                bank[field] = int(change[field])

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
    removed_leg_ids: set[str] = set()
    for removal in overlay.get("removeLegs", []):
        identifier = str(removal["legId"])
        leg = legs_by_id.get(identifier)
        if leg is None:
            raise ValueError(f"Cannot remove missing leg {identifier}")
        expected_fields = {
            "expectedRoute": "route",
            "expectedOrigin": "origin",
            "expectedDestination": "destination",
            "expectedDepartureMinute": "departureMinute",
            "expectedArrivalMinute": "arrivalMinute",
        }
        for expected_key, field in expected_fields.items():
            if expected_key in removal and leg[field] != removal[expected_key]:
                raise ValueError(
                    f"Stale overlay for {identifier}: expected {field} "
                    f"{removal[expected_key]}, found {leg[field]}"
                )
        removed_leg_ids.add(identifier)
        del legs_by_id[identifier]
    if removed_leg_ids:
        result["legs"] = [
            leg for leg in result["legs"] if leg["id"] not in removed_leg_ids
        ]
        result["bankAssignments"] = [
            assignment
            for assignment in result.get("bankAssignments", [])
            if assignment["legId"] not in removed_leg_ids
        ]

    # Resolve all leg exchanges against the original route identities before
    # relabeling routes. This permits simultaneous suffix swaps without
    # duplicating flights or losing their IDs and bank assignments.
    leg_changes = overlay.get("legReassignments", [])
    original_identities: dict[int, set[tuple[str, str, int]]] = defaultdict(set)
    for leg in result["legs"]:
        original_identities[int(leg["route"])].add(
            (str(leg["line"]), str(leg["fleet"]), int(leg["day"]))
        )
    moved_ids: set[str] = set()
    moved_routes: set[int] = set()
    for change in leg_changes:
        identifier = str(change["legId"])
        if identifier in moved_ids:
            raise ValueError(f"Duplicate leg reassignment: {identifier}")
        leg = legs_by_id.get(identifier)
        if leg is None:
            raise ValueError(f"Cannot reassign missing leg {identifier}")
        source = int(leg["route"])
        if source != int(change["expectedRoute"]):
            raise ValueError(f"Stale leg reassignment for {identifier}: route {source}")
        if ("expectedSequenceWithinRoute" in change
                and leg["sequenceWithinRoute"] != change["expectedSequenceWithinRoute"]):
            raise ValueError(f"Stale leg reassignment for {identifier}: sequence")
        target = int(change["targetRoute"])
        identities = original_identities.get(target, set())
        if len(identities) != 1:
            raise ValueError(f"Leg reassignment needs one target route identity: {target}")
        line, fleet, day = next(iter(identities))
        if fleet != leg["fleet"]:
            raise ValueError(f"Leg reassignment cannot change fleet: {identifier}")
        leg.update(route=target, line=line, day=day)
        moved_ids.add(identifier)
        moved_routes.update((source, target))

    route_changes = overlay.get("routeReassignments", [])
    if route_changes:
        changes_by_source: dict[int, dict[str, Any]] = {}
        for change in route_changes:
            source = int(change["sourceRoute"])
            if source in changes_by_source:
                raise ValueError(f"Duplicate route reassignment source: {source}")
            changes_by_source[source] = change
        source_route_legs = {
            source: [
                leg for leg in result["legs"] if int(leg["route"]) == source
            ]
            for source in changes_by_source
        }
        for source, change in changes_by_source.items():
            route_legs = source_route_legs[source]
            if not route_legs:
                raise ValueError(f"Cannot reassign missing route {source}")
            identities = {
                (str(leg["line"]), int(leg["day"]), str(leg["fleet"]))
                for leg in route_legs
            }
            if len(identities) != 1:
                raise ValueError(f"Route {source} does not have one identity")
            line, day, fleet = next(iter(identities))
            expected = (
                str(change.get("expectedLine", line)),
                int(change.get("expectedDay", day)),
                str(change.get("expectedFleet", fleet)),
            )
            if (line, day, fleet) != expected:
                raise ValueError(
                    f"Stale route reassignment for {source}: expected {expected}, "
                    f"found {(line, day, fleet)}"
                )
            for leg in route_legs:
                leg["route"] = int(change.get("targetRoute", source))
                leg["line"] = str(change.get("line", line))
                leg["day"] = int(change.get("day", day))

    touched_routes: set[int] = moved_routes.copy()
    for change in route_changes:
        touched_routes.add(int(change["sourceRoute"]))
        touched_routes.add(int(change.get("targetRoute", change["sourceRoute"])))
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
