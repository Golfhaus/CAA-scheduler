from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .bank_placement import TIMEZONE_OFFSETS, _block_minutes, _curfew_status
from .demand import load_demand_sources_from_manifest


def _utc_minute(local_minute: int, station: str, cities: dict[str, dict[str, Any]]) -> int:
    return (local_minute - TIMEZONE_OFFSETS[cities[station]["timezone"]]) % 1440


def _local_minute(utc_minute: int, station: str, cities: dict[str, dict[str, Any]]) -> int:
    return (utc_minute + TIMEZONE_OFFSETS[cities[station]["timezone"]]) % 1440


def _connection_wait(arrival_utc: int, departure_utc: int, minimum_turn: int) -> int:
    wait = (departure_utc - arrival_utc) % 1440
    return wait if wait >= minimum_turn else wait + 1440


def _hungarian(cost: list[list[int]]) -> list[int]:
    """Return the minimum-cost column for every row of a square matrix."""
    size = len(cost)
    if not size:
        return []
    if any(len(row) != size for row in cost):
        raise ValueError("Hungarian assignment requires a square matrix")
    u = [0] * (size + 1)
    v = [0] * (size + 1)
    matched_row = [0] * (size + 1)
    path = [0] * (size + 1)
    for row_index in range(1, size + 1):
        matched_row[0] = row_index
        minimum = [math.inf] * (size + 1)
        used = [False] * (size + 1)
        column = 0
        while True:
            used[column] = True
            current_row = matched_row[column]
            delta = math.inf
            next_column = 0
            for candidate in range(1, size + 1):
                if used[candidate]:
                    continue
                reduced = cost[current_row - 1][candidate - 1] - u[current_row] - v[candidate]
                if reduced < minimum[candidate]:
                    minimum[candidate] = reduced
                    path[candidate] = column
                if minimum[candidate] < delta:
                    delta = minimum[candidate]
                    next_column = candidate
            for candidate in range(size + 1):
                if used[candidate]:
                    u[matched_row[candidate]] += int(delta)
                    v[candidate] -= int(delta)
                else:
                    minimum[candidate] -= delta
            column = next_column
            if matched_row[column] == 0:
                break
        while True:
            previous = path[column]
            matched_row[column] = matched_row[previous]
            column = previous
            if column == 0:
                break
    assignment = [0] * size
    for column in range(1, size + 1):
        assignment[matched_row[column] - 1] = column - 1
    return assignment


def _banked_legs(
    bank_plan: dict[str, Any], cities: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    return {
        row["id"]: {
            **row,
            "source": "bank_plan",
            "departureUtcMinute": _utc_minute(
                int(row["departureMinute"]), row["origin"], cities
            ),
        }
        for row in bank_plan["placements"]
    }


def _match_station_successors(
    legs: dict[str, dict[str, Any]], minimum_turn: int
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    successors: dict[str, str] = {}
    gaps = []
    fleet_stations = sorted(
        {
            (leg["fleet"], station)
            for leg in legs.values()
            for station in (leg["origin"], leg["destination"])
        }
    )
    for fleet, station in fleet_stations:
        arrivals = sorted(
            (
                leg
                for leg in legs.values()
                if leg["fleet"] == fleet and leg["destination"] == station
            ),
            key=lambda row: row["id"],
        )
        departures = sorted(
            (
                leg
                for leg in legs.values()
                if leg["fleet"] == fleet and leg["origin"] == station
            ),
            key=lambda row: row["id"],
        )
        if len(arrivals) != len(departures):
            raise ValueError(
                f"Directional fleet imbalance at {station}/{fleet}: "
                f"{len(arrivals)} arrivals, {len(departures)} departures"
            )
        costs = []
        for arrival in arrivals:
            arrival_utc = arrival["departureUtcMinute"] + arrival["blockMinutes"]
            costs.append(
                [
                    _connection_wait(
                        arrival_utc,
                        departure["departureUtcMinute"],
                        minimum_turn,
                    )
                    for departure in departures
                ]
            )
        for row_index, column_index in enumerate(_hungarian(costs)):
            arrival = arrivals[row_index]
            departure = departures[column_index]
            wait = costs[row_index][column_index]
            successors[arrival["id"]] = departure["id"]
            arrival_utc = arrival["departureUtcMinute"] + arrival["blockMinutes"]
            gaps.append(
                {
                    "fleet": fleet,
                    "station": station,
                    "arrivingLegId": arrival["id"],
                    "lastLegId": arrival["id"],
                    "nextLegId": departure["id"],
                    "cursorUtcMinute": arrival_utc,
                    "nextDepartureUtcMinute": arrival_utc + wait,
                    "originalWaitMinutes": wait,
                    "insertedRoundTrips": 0,
                }
            )
    return successors, gaps


def _nonhub_units(
    frequency_plan: dict[str, Any], hubs: set[str]
) -> list[dict[str, Any]]:
    units = []
    for market in frequency_plan["markets"]:
        if market["origin"] in hubs or market["destination"] in hubs:
            continue
        ordinal = 0
        for allocation in market["allocations"]:
            for _ in range(allocation["roundTrips"]):
                ordinal += 1
                units.append(
                    {
                        "market": market,
                        "fleet": allocation["fleet"],
                        "ordinal": ordinal,
                    }
                )
    return sorted(
        units,
        key=lambda row: (
            -row["market"]["twoWayDemand"],
            row["market"]["origin"],
            row["market"]["destination"],
            row["fleet"],
            row["ordinal"],
        ),
    )


def _insertion_candidate(
    gap: dict[str, Any],
    anchor: str,
    other: str,
    block: int,
    policy: dict[str, Any],
    cities: dict[str, dict[str, Any]],
    minimum_turn: int,
) -> dict[str, int] | None:
    earliest = gap["cursorUtcMinute"] + minimum_turn
    latest = gap["nextDepartureUtcMinute"] - (2 * block + 2 * minimum_turn)
    if latest < earliest:
        return None
    candidates = list(range(earliest, latest + 1, 5))
    if latest not in candidates:
        candidates.append(latest)
    for departure_utc in candidates:
        departure = _local_minute(departure_utc, anchor, cities)
        first_arrival_utc = departure_utc + block
        first_arrival = _local_minute(first_arrival_utc, other, cities)
        return_departure_utc = first_arrival_utc + minimum_turn
        return_departure = _local_minute(return_departure_utc, other, cities)
        return_arrival_utc = return_departure_utc + block
        return_arrival = _local_minute(return_arrival_utc, anchor, cities)
        if (
            _curfew_status(anchor, departure, first_arrival, policy) == "pass"
            and _curfew_status(
                other, return_departure, return_arrival, policy
            )
            == "pass"
        ):
            return {
                "departureUtc": departure_utc,
                "departure": departure,
                "firstArrival": first_arrival,
                "returnDepartureUtc": return_departure_utc,
                "returnDeparture": return_departure,
                "returnArrivalUtc": return_arrival_utc,
                "returnArrival": return_arrival,
            }
    return None


def _standalone_candidate(
    anchor: str,
    other: str,
    block: int,
    policy: dict[str, Any],
    cities: dict[str, dict[str, Any]],
    minimum_turn: int,
) -> dict[str, int] | None:
    """Find a curfew-safe daily round trip when no routed gap can hold it."""
    for departure in range(180, 1620, 5):
        departure_local = departure % 1440
        departure_utc = _utc_minute(departure_local, anchor, cities)
        first_arrival_utc = departure_utc + block
        first_arrival = _local_minute(first_arrival_utc, other, cities)
        return_departure_utc = first_arrival_utc + minimum_turn
        return_departure = _local_minute(return_departure_utc, other, cities)
        return_arrival_utc = return_departure_utc + block
        return_arrival = _local_minute(return_arrival_utc, anchor, cities)
        next_daily_departure_utc = departure_utc + 1440
        if next_daily_departure_utc - return_arrival_utc < minimum_turn:
            continue
        if (
            _curfew_status(
                anchor, departure_local, first_arrival, policy
            )
            == "pass"
            and _curfew_status(
                other, return_departure, return_arrival, policy
            )
            == "pass"
        ):
            return {
                "departureUtc": departure_utc,
                "departure": departure_local,
                "firstArrival": first_arrival,
                "returnDepartureUtc": return_departure_utc,
                "returnDeparture": return_departure,
                "returnArrivalUtc": return_arrival_utc,
                "returnArrival": return_arrival,
            }
    return None


def _insert_nonhub_flying(
    legs: dict[str, dict[str, Any]],
    successors: dict[str, str],
    gaps: list[dict[str, Any]],
    units: list[dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    cities: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    unplaced = []
    for unit in units:
        market = unit["market"]
        fleet = unit["fleet"]
        block = _block_minutes(
            market["origin"], market["destination"], profiles[fleet], cities
        )
        options = []
        for gap in gaps:
            if (
                gap["fleet"] != fleet
                or gap["station"]
                not in {market["origin"], market["destination"]}
            ):
                continue
            anchor = gap["station"]
            other = (
                market["destination"]
                if anchor == market["origin"]
                else market["origin"]
            )
            candidate = _insertion_candidate(
                gap, anchor, other, block, policy, cities, minimum_turn
            )
            if candidate is None:
                continue
            remaining = (
                gap["nextDepartureUtcMinute"]
                - candidate["returnArrivalUtc"]
                - minimum_turn
            )
            options.append(
                (
                    remaining,
                    gap["originalWaitMinutes"],
                    gap["station"],
                    gap["arrivingLegId"],
                    gap,
                    candidate,
                    anchor,
                    other,
                )
            )
        base = (
            f"{market['origin']}-{market['destination']}-{fleet}-"
            f"{unit['ordinal']}-P2P"
        )
        outbound_id = f"{base}-OUT"
        inbound_id = f"{base}-IN"
        if options:
            *_, gap, candidate, anchor, other = min(options)
            source = "gap_insertion"
        else:
            standalone_options = []
            for anchor, other in (
                (market["origin"], market["destination"]),
                (market["destination"], market["origin"]),
            ):
                candidate = _standalone_candidate(
                    anchor,
                    other,
                    block,
                    policy,
                    cities,
                    minimum_turn,
                )
                if candidate is not None:
                    standalone_options.append(
                        (candidate["departureUtc"], anchor, other, candidate)
                    )
            if not standalone_options:
                unplaced.append(
                    {
                        "market": [market["origin"], market["destination"]],
                        "fleet": fleet,
                        "roundTripOrdinal": unit["ordinal"],
                        "reason": "No curfew-safe daily round-trip placement exists",
                    }
                )
                continue
            _, anchor, other, candidate = min(standalone_options)
            source = "standalone_cycle"
        legs[outbound_id] = {
            "id": outbound_id,
            "source": source,
            "market": [market["origin"], market["destination"]],
            "classification": market["classification"],
            "fleet": fleet,
            "roundTripOrdinal": unit["ordinal"],
            "direction": "outbound",
            "origin": anchor,
            "destination": other,
            "departureMinute": candidate["departure"],
            "arrivalMinute": candidate["firstArrival"],
            "departureUtcMinute": candidate["departureUtc"] % 1440,
            "blockMinutes": block,
            "bankTouches": [],
            "curfewStatus": "pass",
        }
        legs[inbound_id] = {
            "id": inbound_id,
            "source": source,
            "market": [market["origin"], market["destination"]],
            "classification": market["classification"],
            "fleet": fleet,
            "roundTripOrdinal": unit["ordinal"],
            "direction": "inbound",
            "origin": other,
            "destination": anchor,
            "departureMinute": candidate["returnDeparture"],
            "arrivalMinute": candidate["returnArrival"],
            "departureUtcMinute": candidate["returnDepartureUtc"] % 1440,
            "blockMinutes": block,
            "bankTouches": [],
            "curfewStatus": "pass",
        }
        if source == "gap_insertion":
            previous = gap["lastLegId"]
            successors[previous] = outbound_id
            successors[outbound_id] = inbound_id
            successors[inbound_id] = gap["nextLegId"]
            gap["lastLegId"] = inbound_id
            gap["cursorUtcMinute"] = candidate["returnArrivalUtc"]
            gap["insertedRoundTrips"] += 1
        else:
            successors[outbound_id] = inbound_id
            successors[inbound_id] = outbound_id
    return unplaced


def _ron_count(
    arrival_utc: int,
    next_departure_utc: int,
    station: str,
    cities: dict[str, dict[str, Any]],
) -> int:
    offset = TIMEZONE_OFFSETS[cities[station]["timezone"]]
    local_start = arrival_utc + offset
    local_end = next_departure_utc + offset
    return max(
        0,
        math.floor((local_end - 180) / 1440)
        - math.floor((local_start - 180) / 1440),
    )


def _cycles(
    legs: dict[str, dict[str, Any]],
    successors: dict[str, str],
    policy: dict[str, Any],
    cities: dict[str, dict[str, Any]],
    *,
    single_target_full_gap: bool = False,
) -> list[dict[str, Any]]:
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    target_cities = set(policy["ronTargetCities"])
    seen: set[str] = set()
    cycles = []
    for seed in sorted(legs):
        if seed in seen:
            continue
        identifiers = []
        current = seed
        while current not in seen:
            seen.add(current)
            identifiers.append(current)
            current = successors[current]
        smallest = min(range(len(identifiers)), key=lambda index: identifiers[index])
        identifiers = identifiers[smallest:] + identifiers[:smallest]
        duration = 0
        ron_stops = []
        target_positions = []
        for identifier in identifiers:
            leg = legs[identifier]
            next_leg = legs[successors[identifier]]
            arrival_utc = leg["departureUtcMinute"] + leg["blockMinutes"]
            wait = _connection_wait(
                arrival_utc,
                next_leg["departureUtcMinute"],
                minimum_turn,
            )
            next_departure_utc = arrival_utc + wait
            overnight_count = _ron_count(
                arrival_utc,
                next_departure_utc,
                leg["destination"],
                cities,
            )
            duration += leg["blockMinutes"] + wait
            if overnight_count:
                stop = {
                    "station": leg["destination"],
                    "afterLegId": identifier,
                    "beforeLegId": successors[identifier],
                    "waitMinutes": wait,
                    "overnightCount": overnight_count,
                    "targetCity": leg["destination"] in target_cities,
                }
                ron_stops.append(stop)
                if stop["targetCity"]:
                    target_positions.append(duration)
        if duration % 1440:
            raise ValueError(
                f"Routing cycle beginning {seed} is not an integer number of days"
            )
        cycle_days = duration // 1440
        if not target_positions:
            maximum_target_gap = cycle_days
        else:
            positions = sorted(position % duration for position in target_positions)
            if len(positions) == 1 and not single_target_full_gap:
                gaps = [0]
            else:
                gaps = [
                    following - position
                    for position, following in zip(positions, positions[1:])
                ]
                gaps.append(duration - positions[-1] + positions[0])
            maximum_target_gap = max(1, math.ceil(max(gaps) / 1440))
        cycles.append(
            {
                "id": f"CYCLE-{len(cycles) + 1:03d}",
                "fleet": legs[identifiers[0]]["fleet"],
                "legCount": len(identifiers),
                "durationMinutes": duration,
                "aircraftRequired": cycle_days,
                "maximumDaysWithoutTargetRon": maximum_target_gap,
                "legIds": identifiers,
                "ronStops": ron_stops,
            }
        )
    return cycles


def _artifact_leg(leg: dict[str, Any]) -> dict[str, Any]:
    """Keep the route artifact self-contained without duplicating planning detail."""
    keys = (
        "id",
        "source",
        "fleet",
        "origin",
        "destination",
        "departureMinute",
        "arrivalMinute",
        "departureUtcMinute",
        "blockMinutes",
        "curfewStatus",
    )
    return {key: leg[key] for key in keys}


def build_aircraft_route_plan(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    planning_rules: dict[str, Any],
) -> dict[str, Any]:
    if frequency_plan.get("status") != "pass" or bank_plan.get("status") != "pass":
        raise ValueError("Aircraft routing requires passing frequency and bank plans")
    cities = {
        city["code"]: city for city in canonical["cities"] if city.get("active")
    }
    policy = canonical["operatingPolicy"]
    hubs = set(policy["hubs"])
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    profiles = {
        row["fleet"]: row
        for row in planning_rules["frequencyAllocation"]["fleetProfiles"]
    }
    legs = _banked_legs(bank_plan, cities)
    successors, gaps = _match_station_successors(legs, minimum_turn)
    units = _nonhub_units(frequency_plan, hubs)
    unplaced = _insert_nonhub_flying(
        legs, successors, gaps, units, profiles, policy, cities
    )
    cycles = _cycles(legs, successors, policy, cities)

    planned_legs = int(frequency_plan["summary"]["plannedLegs"])
    fleet_plan = {}
    for fleet, configured in canonical["schedule"]["fleetCounts"].items():
        fleet_cycles = [cycle for cycle in cycles if cycle["fleet"] == fleet]
        required = sum(cycle["aircraftRequired"] for cycle in fleet_cycles)
        fleet_plan[fleet] = {
            "configuredAircraft": configured,
            "requiredAircraft": required,
            "shortfall": max(0, required - configured),
            "remainingAircraft": max(0, configured - required),
            "cycles": len(fleet_cycles),
            "routedLegs": sum(cycle["legCount"] for cycle in fleet_cycles),
        }

    turn_violations = []
    curfew_violations = []
    continuity_violations = []
    for identifier, next_identifier in successors.items():
        leg = legs[identifier]
        next_leg = legs[next_identifier]
        if leg["destination"] != next_leg["origin"] or leg["fleet"] != next_leg["fleet"]:
            continuity_violations.append([identifier, next_identifier])
        arrival_utc = leg["departureUtcMinute"] + leg["blockMinutes"]
        wait = _connection_wait(
            arrival_utc, next_leg["departureUtcMinute"], minimum_turn
        )
        if wait < minimum_turn:
            turn_violations.append([identifier, next_identifier, wait])
    for leg in legs.values():
        if (
            _curfew_status(
                leg["origin"],
                int(leg["departureMinute"]),
                int(leg["arrivalMinute"]),
                policy,
            )
            == "fail"
        ):
            curfew_violations.append(leg["id"])

    ron_cities = {
        stop["station"]
        for cycle in cycles
        for stop in cycle["ronStops"]
    }
    exemptions = set(policy.get("destinationRonExemptions", []))
    missing_destination_rons = sorted(
        city["code"]
        for city in cities.values()
        if city["role"] == "destination"
        and city["code"] not in exemptions
        and city["code"] not in ron_cities
    )
    ron_limit = int(planning_rules["routing"]["rollingRonWindowDays"])
    ron_grace = int(policy["rollingRonGraceDays"])
    rolling_violations = [
        cycle["id"]
        for cycle in cycles
        if cycle["maximumDaysWithoutTargetRon"] > ron_limit + ron_grace
    ]
    capacity_shortfall = sum(row["shortfall"] for row in fleet_plan.values())
    checks = [
        {
            "id": "service_coverage",
            "status": "pass" if len(legs) == planned_legs and not unplaced else "fail",
            "message": (
                f"All {planned_legs} proposed legs are included in routing cycles"
                if len(legs) == planned_legs and not unplaced
                else f"{len(unplaced)} proposed non-hub round trips remain unplaced"
            ),
        },
        {
            "id": "routing_continuity",
            "status": "pass" if not continuity_violations else "fail",
            "message": (
                "Every routed leg continues from the same station and fleet"
                if not continuity_violations
                else f"{len(continuity_violations)} route connections are discontinuous"
            ),
        },
        {
            "id": "minimum_turns",
            "status": "pass" if not turn_violations else "fail",
            "message": (
                f"Every route connection meets the {minimum_turn}-minute floor"
                if not turn_violations
                else f"{len(turn_violations)} route connections miss the turn floor"
            ),
        },
        {
            "id": "fleet_capacity",
            "status": "pass" if not capacity_shortfall else "fail",
            "message": (
                "Every fleet's routed aircraft requirement fits its schedule-specific count"
                if not capacity_shortfall
                else f"Routing needs {capacity_shortfall} aircraft beyond the configured fleet"
            ),
        },
        {
            "id": "curfew_enforcement",
            "status": "pass" if not curfew_violations else "fail",
            "hardStop": True,
            "message": (
                "Every routed departure is curfew compliant"
                if not curfew_violations
                else f"{len(curfew_violations)} routed departures violate a curfew"
            ),
        },
        {
            "id": "destination_ron_coverage",
            "status": "pass" if not missing_destination_rons else "fail",
            "message": (
                "Every non-exempt destination receives a routed overnight"
                if not missing_destination_rons
                else "Destinations without a routed overnight: "
                + ", ".join(missing_destination_rons)
            ),
        },
        {
            "id": "rolling_target_ron",
            "status": "pass" if not rolling_violations else "fail",
            "message": (
                f"Every cycle reaches a target RON within {ron_limit + ron_grace} days"
                if not rolling_violations
                else f"{len(rolling_violations)} cycles exceed the target-RON window"
            ),
        },
    ]
    failed = sum(check["status"] == "fail" for check in checks)
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "banked_aircraft_cycle_plan",
        "planningRulesId": planning_rules["id"],
        "operatingPolicyId": policy["id"],
        "status": "pass" if not failed else "fail",
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
            "plannedLegs": planned_legs,
            "routedLegs": len(legs),
            "bankedLegs": int(bank_plan["summary"]["placedLegs"]),
            "insertedNonHubLegs": len(legs) - int(bank_plan["summary"]["placedLegs"]),
            "unplacedRoundTrips": len(unplaced),
            "cycles": len(cycles),
            "configuredAircraft": sum(canonical["schedule"]["fleetCounts"].values()),
            "requiredAircraft": sum(row["requiredAircraft"] for row in fleet_plan.values()),
            "aircraftShortfall": capacity_shortfall,
            "curfewViolations": len(curfew_violations),
            "destinationsWithoutRon": len(missing_destination_rons),
            "rollingRonViolations": len(rolling_violations),
        },
        "checks": checks,
        "fleetPlan": fleet_plan,
        "legs": [
            _artifact_leg(row)
            for row in sorted(legs.values(), key=lambda row: row["id"])
        ],
        "cycles": cycles,
        "unplaced": unplaced,
        "diagnostics": {
            "continuityViolations": continuity_violations,
            "turnViolations": turn_violations,
            "curfewViolations": curfew_violations,
            "missingDestinationRons": missing_destination_rons,
            "rollingRonViolations": rolling_violations,
        },
        "limitations": [
            "This stage exposes whether the independently placed bank plan can be "
            "covered by the selected fleet; it does not silently add aircraft.",
            "A capacity failure requires deterministic retiming, bank reassignment, "
            "fleet reassignment, or frequency repair before canonical publication.",
            "Flight numbers and canonical Line/Day/Route identifiers are assigned "
            "only after the routing checks pass.",
        ],
    }


def build_aircraft_route_plan_from_manifest(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loaded = load_demand_sources_from_manifest(manifest_path, repo_root)
    if loaded["manifest"]["id"] != frequency_plan["demandDataVersion"]:
        raise ValueError("Frequency plan version does not match the routing manifest")
    if bank_plan["planningRulesId"] != loaded["planningRules"]["id"]:
        raise ValueError("Bank plan version does not match the routing manifest")
    return build_aircraft_route_plan(
        canonical, frequency_plan, bank_plan, loaded["planningRules"]
    )
