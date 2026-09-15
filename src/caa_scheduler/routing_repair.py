from __future__ import annotations

import random
from copy import deepcopy
from collections import defaultdict
from pathlib import Path
from typing import Any

from .bank_placement import TIMEZONE_OFFSETS, _block_minutes, _curfew_status
from .demand import load_demand_sources_from_manifest


SEARCH_SEEDS = 128
ENDPOINT_LOOKBACKS = range(1, 9)
TIME_STEP_MINUTES = 5


def _utc_minute(local_minute: int, station: str, cities: dict[str, dict[str, Any]]) -> int:
    return (local_minute - TIMEZONE_OFFSETS[cities[station]["timezone"]]) % 1440


def _local_minute(utc_minute: int, station: str, cities: dict[str, dict[str, Any]]) -> int:
    return (utc_minute + TIMEZONE_OFFSETS[cities[station]["timezone"]]) % 1440


def _leg_inventory(
    frequency_plan: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    cities: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    by_fleet: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for market in frequency_plan["markets"]:
        for allocation in market["allocations"]:
            fleet = allocation["fleet"]
            block = _block_minutes(
                market["origin"], market["destination"], profiles[fleet], cities
            )
            for ordinal in range(1, int(allocation["roundTrips"]) + 1):
                base = (
                    f"{market['origin']}-{market['destination']}-{fleet}-"
                    f"{ordinal:02d}"
                )
                for direction, origin, destination in (
                    ("OUT", market["origin"], market["destination"]),
                    ("IN", market["destination"], market["origin"]),
                ):
                    by_fleet[fleet].append(
                        {
                            "id": f"{base}-{direction}",
                            "source": "topology_repair",
                            "market": [market["origin"], market["destination"]],
                            "classification": market["classification"],
                            "fleet": fleet,
                            "origin": origin,
                            "destination": destination,
                            "blockMinutes": block,
                        }
                    )
    return dict(by_fleet)


def _euler_circuit(legs: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    adjacency: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for leg in sorted(legs, key=lambda row: row["id"]):
        adjacency[leg["origin"]].append(leg)
    randomizer = random.Random(seed)
    for station in sorted(adjacency):
        randomizer.shuffle(adjacency[station])

    stack: list[tuple[str, dict[str, Any] | None]] = [(min(adjacency), None)]
    circuit: list[dict[str, Any]] = []
    while stack:
        station, incoming = stack[-1]
        if adjacency[station]:
            leg = adjacency[station].pop()
            stack.append((leg["destination"], leg))
        else:
            stack.pop()
            if incoming is not None:
                circuit.append(incoming)
    circuit.reverse()
    if len(circuit) != len(legs):
        raise ValueError("Routing repair inventory is not one connected fleet circuit")
    return circuit


def _schedule_prefix(
    legs: list[dict[str, Any]],
    start_index: int,
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    boundary = _utc_minute(180, legs[start_index]["origin"], cities)
    cursor = boundary
    scheduled: list[dict[str, Any]] = []
    while start_index + len(scheduled) < len(legs):
        leg = legs[start_index + len(scheduled)]
        earliest = cursor + (minimum_turn if scheduled else 0)
        latest = boundary + 1440 - int(leg["blockMinutes"])
        departure_utc = next(
            (
                minute
                for minute in range(earliest, latest + 1, TIME_STEP_MINUTES)
                if _curfew_status(
                    leg["origin"],
                    _local_minute(minute, leg["origin"], cities),
                    _local_minute(
                        minute + int(leg["blockMinutes"]),
                        leg["destination"],
                        cities,
                    ),
                    policy,
                )
                == "pass"
            ),
            None,
        )
        if departure_utc is None:
            break
        arrival_utc = departure_utc + int(leg["blockMinutes"])
        scheduled.append(
            {
                **leg,
                "departureMinute": _local_minute(
                    departure_utc, leg["origin"], cities
                ),
                "arrivalMinute": _local_minute(
                    arrival_utc, leg["destination"], cities
                ),
                "departureUtcMinute": departure_utc % 1440,
                "arrivalUtcMinute": arrival_utc,
                "curfewStatus": "pass",
            }
        )
        cursor = arrival_utc
    return scheduled


def _maximum_non_target_gap(routes: list[dict[str, Any]], targets: set[str]) -> int:
    if not routes:
        return 0
    flags = [route["ronStation"] in targets for route in routes]
    if not any(flags):
        return len(routes)
    doubled = flags + flags
    maximum = current = 0
    for flag in doubled:
        current = 0 if flag else current + 1
        maximum = max(maximum, current)
    return min(maximum, len(routes))


def _partition(
    circuit: list[dict[str, Any]],
    lookback: int,
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    destinations: set[str],
    targets: set[str],
    priority_destinations: set[str] | None = None,
) -> list[dict[str, Any]]:
    priority_destinations = priority_destinations or set()
    routes: list[dict[str, Any]] = []
    covered: set[str] = set()
    days_without_target = 0
    index = 0
    while index < len(circuit):
        maximum = _schedule_prefix(circuit, index, cities, policy)
        if not maximum:
            raise ValueError(f"No curfew-safe placement exists for {circuit[index]['id']}")
        first_cut = max(1, len(maximum) - lookback + 1)
        if days_without_target >= 9 and any(
            leg["destination"] in targets for leg in maximum
        ):
            first_cut = 1
        choices = []
        for cut in range(first_cut, len(maximum) + 1):
            station = maximum[cut - 1]["destination"]
            choices.append(
                (
                    station in priority_destinations and station not in covered,
                    station in targets and days_without_target >= 8,
                    station in destinations and station not in covered,
                    cut,
                )
            )
        cut = max(choices)[-1]
        route_legs = maximum[:cut]
        ron_station = route_legs[-1]["destination"]
        covered.add(ron_station)
        days_without_target = (
            0 if ron_station in targets else days_without_target + 1
        )
        routes.append({"fleet": route_legs[0]["fleet"], "legs": route_legs, "ronStation": ron_station})
        index += cut
    return routes


def _candidate_score(
    routes: list[dict[str, Any]], destinations: set[str], targets: set[str]
) -> tuple[int, int, int]:
    covered = {route["ronStation"] for route in routes} & destinations
    return (
        len(covered),
        -_maximum_non_target_gap(routes, targets),
        -len(routes),
    )


def _fleet_candidates(
    legs: list[dict[str, Any]],
    configured_aircraft: int,
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    destinations: set[str],
    targets: set[str],
    priority_destinations: set[str],
) -> list[dict[str, Any]]:
    candidates = []
    for seed in range(SEARCH_SEEDS):
        circuit = _euler_circuit(legs, seed)
        for lookback in ENDPOINT_LOOKBACKS:
            routes = _partition(
                circuit,
                lookback,
                cities,
                policy,
                destinations,
                targets,
                priority_destinations,
            )
            if len(routes) > configured_aircraft:
                continue
            candidates.append(
                {
                    "seed": seed,
                    "lookback": lookback,
                    "routes": routes,
                    "score": _candidate_score(routes, destinations, targets),
                }
            )
    if not candidates:
        return []
    candidates.sort(
        key=lambda row: (row["score"], -row["seed"], -row["lookback"]),
        reverse=True,
    )
    # Keeping distinct endpoint sets bounds the global coverage search without
    # making the result dependent on the number of duplicate permutations.
    distinct = []
    signatures = set()
    coverage_ranked = sorted(
        candidates,
        key=lambda row: (
            row["score"][0],
            row["score"][1],
            row["score"][2],
            -row["seed"],
            -row["lookback"],
        ),
        reverse=True,
    )[:128]
    cadence_ranked = sorted(
        candidates,
        key=lambda row: (
            row["score"][1],
            row["score"][0],
            row["score"][2],
            -row["seed"],
            -row["lookback"],
        ),
        reverse=True,
    )[:128]
    capacity_ranked = sorted(
        candidates,
        key=lambda row: (
            row["score"][2],
            row["score"][0],
            row["score"][1],
            -row["seed"],
            -row["lookback"],
        ),
        reverse=True,
    )[:128]
    for candidate in coverage_ranked + cadence_ranked + capacity_ranked:
        signature = tuple(route["ronStation"] for route in candidate["routes"])
        if signature in signatures:
            continue
        signatures.add(signature)
        distinct.append(candidate)
        if len(distinct) == 256:
            break
    return distinct


def _select_candidates(
    candidates: dict[str, list[dict[str, Any]]],
    destinations: set[str],
    targets: set[str],
) -> dict[str, dict[str, Any]]:
    selected = {fleet: rows[0] for fleet, rows in candidates.items()}
    for _ in range(3):
        for fleet in sorted(candidates):
            other_coverage = {
                route["ronStation"]
                for other, candidate in selected.items()
                if other != fleet
                for route in candidate["routes"]
            }
            selected[fleet] = max(
                candidates[fleet],
                key=lambda candidate: (
                    len(
                        (
                            other_coverage
                            | {route["ronStation"] for route in candidate["routes"]}
                        )
                        & destinations
                    ),
                    -_maximum_non_target_gap(candidate["routes"], targets),
                    -len(candidate["routes"]),
                    candidate["score"][0],
                    -candidate["seed"],
                    -candidate["lookback"],
                ),
            )
    return selected


def _split_route(
    routes: list[dict[str, Any]],
    route_index: int,
    cut: int,
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> None:
    route = routes[route_index]
    first = route["legs"][:cut]
    remaining_inventory = [
        {
            key: value
            for key, value in leg.items()
            if key
            not in {
                "departureMinute",
                "arrivalMinute",
                "departureUtcMinute",
                "arrivalUtcMinute",
                "curfewStatus",
            }
        }
        for leg in route["legs"][cut:]
    ]
    second = _schedule_prefix(remaining_inventory, 0, cities, policy)
    if len(second) != len(remaining_inventory):
        raise ValueError("A RON repair split made a previously feasible route infeasible")
    routes[route_index : route_index + 1] = [
        {
            "fleet": route["fleet"],
            "legs": first,
            "ronStation": first[-1]["destination"],
        },
        {
            "fleet": route["fleet"],
            "legs": second,
            "ronStation": second[-1]["destination"],
        },
    ]


def _split_for_destination_coverage(
    routes_by_fleet: dict[str, list[dict[str, Any]]],
    fleet_counts: dict[str, int],
    destinations: set[str],
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[str]:
    while True:
        covered = {
            route["ronStation"]
            for routes in routes_by_fleet.values()
            for route in routes
        }
        missing = sorted(destinations - covered)
        if not missing:
            return []
        options_by_city: dict[str, list[tuple[str, int, int]]] = {}
        for city in missing:
            options = []
            for fleet, routes in routes_by_fleet.items():
                if len(routes) >= int(fleet_counts[fleet]):
                    continue
                for route_index, route in enumerate(routes):
                    for cut in range(1, len(route["legs"])):
                        if route["legs"][cut - 1]["destination"] == city:
                            options.append((fleet, route_index, cut))
            options_by_city[city] = options
        city = min(missing, key=lambda item: (len(options_by_city[item]), item))
        if not options_by_city[city]:
            return missing
        fleet, route_index, cut = min(
            options_by_city[city],
            key=lambda row: (
                len(routes_by_fleet[row[0]]),
                row[0],
                row[1],
                row[2],
            ),
        )
        _split_route(routes_by_fleet[fleet], route_index, cut, cities, policy)


def _repair_target_cadence(
    routes_by_fleet: dict[str, list[dict[str, Any]]],
    fleet_counts: dict[str, int],
    targets: set[str],
    limit: int,
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[str]:
    failures = []
    for fleet, routes in routes_by_fleet.items():
        while _maximum_non_target_gap(routes, targets) > limit:
            if len(routes) >= int(fleet_counts[fleet]):
                failures.append(fleet)
                break
            options = []
            for route_index, route in enumerate(routes):
                for cut in range(1, len(route["legs"])):
                    if route["legs"][cut - 1]["destination"] not in targets:
                        continue
                    simulated = routes[:route_index] + [
                        {
                            "fleet": fleet,
                            "legs": route["legs"][:cut],
                            "ronStation": route["legs"][cut - 1]["destination"],
                        },
                        {
                            "fleet": fleet,
                            "legs": route["legs"][cut:],
                            "ronStation": route["ronStation"],
                        },
                    ] + routes[route_index + 1 :]
                    options.append(
                        (
                            _maximum_non_target_gap(simulated, targets),
                            route_index,
                            cut,
                        )
                    )
            if not options:
                failures.append(fleet)
                break
            _, route_index, cut = min(options)
            _split_route(routes, route_index, cut, cities, policy)
    return sorted(set(failures))


def _bank_alignment(
    leg: dict[str, Any], windows: dict[str, list[tuple[int, int]]]
) -> bool:
    origin_ok = leg["origin"] not in windows or any(
        start <= int(leg["departureMinute"]) < end
        for start, end in windows[leg["origin"]]
    )
    destination_ok = leg["destination"] not in windows or any(
        start <= int(leg["arrivalMinute"]) < end
        for start, end in windows[leg["destination"]]
    )
    return origin_ok and destination_ok


def build_routing_repair_plan(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    planning_rules: dict[str, Any],
) -> dict[str, Any]:
    if frequency_plan.get("status") != "pass" or bank_plan.get("status") != "pass":
        raise ValueError("Routing repair requires passing frequency and bank plans")
    cities = {city["code"]: city for city in canonical["cities"] if city.get("active")}
    policy = canonical["operatingPolicy"]
    fleet_counts = canonical["schedule"]["fleetCounts"]
    profiles = {
        row["fleet"]: row
        for row in planning_rules["frequencyAllocation"]["fleetProfiles"]
    }
    inventory = _leg_inventory(frequency_plan, profiles, cities)
    unsupported = sorted(set(inventory) - set(fleet_counts))
    if unsupported:
        raise ValueError("Routing inventory uses unconfigured fleets: " + ", ".join(unsupported))

    destinations = {
        city["code"]
        for city in cities.values()
        if city["role"] == "destination"
        and city["code"] not in set(policy.get("destinationRonExemptions", []))
    }
    targets = set(policy["ronTargetCities"])
    destination_fleets = {
        destination: {
            fleet
            for fleet, fleet_legs in inventory.items()
            if any(leg["destination"] == destination for leg in fleet_legs)
        }
        for destination in destinations
    }
    candidate_sets = {}
    for fleet, legs in sorted(inventory.items()):
        raw_candidates = _fleet_candidates(
            legs,
            int(fleet_counts[fleet]),
            cities,
            policy,
            destinations,
            targets,
            {
                destination
                for destination, serving_fleets in destination_fleets.items()
                if serving_fleets == {fleet}
            },
        )
        priority_destinations = {
            destination
            for destination, serving_fleets in destination_fleets.items()
            if serving_fleets == {fleet}
        }
        prepared_candidates = []
        for candidate in raw_candidates:
            prepared_routes = {fleet: deepcopy(candidate["routes"])}
            priority_missing = _split_for_destination_coverage(
                prepared_routes,
                {fleet: int(fleet_counts[fleet])},
                priority_destinations,
                cities,
                policy,
            )
            cadence_failures = _repair_target_cadence(
                prepared_routes,
                {fleet: int(fleet_counts[fleet])},
                targets,
                int(planning_rules["routing"]["rollingRonWindowDays"])
                + int(policy["rollingRonGraceDays"]),
                cities,
                policy,
            )
            if priority_missing or cadence_failures:
                continue
            prepared = {
                **candidate,
                "routes": prepared_routes[fleet],
                "score": _candidate_score(
                    prepared_routes[fleet], destinations, targets
                ),
            }
            prepared_candidates.append(prepared)
            if len(prepared_candidates) == 64:
                break
        candidate_sets[fleet] = prepared_candidates
        if not candidate_sets[fleet]:
            candidate_sets[fleet] = []
    infeasible_fleets = sorted(fleet for fleet, rows in candidate_sets.items() if not rows)
    selected = (
        _select_candidates(candidate_sets, destinations, targets)
        if not infeasible_fleets
        else {}
    )
    routes_by_fleet = {
        fleet: list(candidate["routes"]) for fleet, candidate in selected.items()
    }
    rolling_limit = int(planning_rules["routing"]["rollingRonWindowDays"]) + int(
        policy["rollingRonGraceDays"]
    )
    cadence_failures = _repair_target_cadence(
        routes_by_fleet,
        fleet_counts,
        targets,
        rolling_limit,
        cities,
        policy,
    )
    missing = (
        _split_for_destination_coverage(
            routes_by_fleet, fleet_counts, destinations, cities, policy
        )
        if routes_by_fleet
        else sorted(destinations)
    )

    routes = []
    legs = []
    for fleet in sorted(routes_by_fleet):
        for ordinal, route in enumerate(routes_by_fleet[fleet], 1):
            route_id = f"REPAIR-{fleet}-{ordinal:03d}"
            route_legs = []
            for sequence, leg in enumerate(route["legs"], 1):
                artifact_leg = {**leg, "routeId": route_id, "sequence": sequence}
                legs.append(artifact_leg)
                route_legs.append(leg["id"])
            routes.append(
                {
                    "id": route_id,
                    "fleet": fleet,
                    "legCount": len(route_legs),
                    "startStation": route["legs"][0]["origin"],
                    "ronStation": route["ronStation"],
                    "legIds": route_legs,
                }
            )

    windows = {
        hub["hub"]: [
            (int(bank["startMinute"]), int(bank["endMinute"]))
            for bank in hub["banks"]
        ]
        for hub in bank_plan["hubs"]
    }
    bank_touch_legs = [
        leg for leg in legs if leg["origin"] in windows or leg["destination"] in windows
    ]
    bank_aligned = [leg for leg in bank_touch_legs if _bank_alignment(leg, windows)]
    curfew_violations = [leg["id"] for leg in legs if leg["curfewStatus"] != "pass"]
    continuity_violations = []
    turn_violations = []
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    for route in routes:
        route_legs = [leg for leg in legs if leg["routeId"] == route["id"]]
        for current, following in zip(route_legs, route_legs[1:]):
            if current["destination"] != following["origin"] or current["fleet"] != following["fleet"]:
                continuity_violations.append([current["id"], following["id"]])
            wait = int(following["departureUtcMinute"]) - (
                int(current["departureUtcMinute"]) + int(current["blockMinutes"])
            )
            if wait < 0:
                wait += 1440
            if wait < minimum_turn:
                turn_violations.append([current["id"], following["id"], wait])
    for fleet in sorted(routes_by_fleet):
        fleet_routes = routes_by_fleet[fleet]
        for current, following in zip(
            fleet_routes, fleet_routes[1:] + fleet_routes[:1]
        ):
            if current["ronStation"] != following["legs"][0]["origin"]:
                continuity_violations.append(
                    [current["legs"][-1]["id"], following["legs"][0]["id"]]
                )

    fleet_plan = {}
    for fleet, configured in fleet_counts.items():
        fleet_routes = [route for route in routes if route["fleet"] == fleet]
        required = len(fleet_routes)
        fleet_plan[fleet] = {
            "configuredAircraft": int(configured),
            "requiredAircraft": required,
            "shortfall": max(0, required - int(configured)),
            "remainingAircraft": max(0, int(configured) - required),
            "routes": required,
            "routedLegs": sum(route["legCount"] for route in fleet_routes),
            "searchSeed": selected.get(fleet, {}).get("seed"),
            "endpointLookback": selected.get(fleet, {}).get("lookback"),
            "maximumDaysWithoutTargetRon": _maximum_non_target_gap(
                fleet_routes, targets
            ),
        }
    rolling_violations = [
        fleet
        for fleet, row in fleet_plan.items()
        if row["maximumDaysWithoutTargetRon"] > rolling_limit
    ]
    rolling_violations = sorted(set(rolling_violations) | set(cadence_failures))
    capacity_shortfall = sum(row["shortfall"] for row in fleet_plan.values())
    planned_legs = int(frequency_plan["summary"]["plannedLegs"])
    checks = [
        {
            "id": "service_coverage",
            "status": "pass" if len(legs) == planned_legs else "fail",
            "message": f"All {planned_legs} proposed legs are retained in the repair topology",
        },
        {
            "id": "routing_continuity",
            "status": "pass" if not continuity_violations else "fail",
            "message": "Every repaired route is station- and fleet-continuous" if not continuity_violations else f"{len(continuity_violations)} repaired connections are discontinuous",
        },
        {
            "id": "minimum_turns",
            "status": "pass" if not turn_violations else "fail",
            "message": f"Every repaired connection meets the {minimum_turn}-minute floor" if not turn_violations else f"{len(turn_violations)} repaired connections miss the turn floor",
        },
        {
            "id": "fleet_capacity",
            "status": "pass" if not capacity_shortfall and not infeasible_fleets else "fail",
            "message": "The topology fits the fleet counts selected for this schedule" if not capacity_shortfall and not infeasible_fleets else "The topology search did not fit every configured fleet",
        },
        {
            "id": "curfew_enforcement",
            "status": "pass" if not curfew_violations else "fail",
            "hardStop": True,
            "message": "Every repaired leg is curfew compliant" if not curfew_violations else f"{len(curfew_violations)} repaired legs violate a curfew",
        },
        {
            "id": "destination_ron_coverage",
            "status": "pass" if not missing else "fail",
            "message": "Every non-exempt destination is a repaired route endpoint" if not missing else "Destinations without a repaired RON endpoint: " + ", ".join(missing),
        },
        {
            "id": "rolling_target_ron",
            "status": "pass" if not rolling_violations else "fail",
            "message": f"Every fleet circuit reaches a target RON within {rolling_limit} route days" if not rolling_violations else "Fleet circuits beyond the target-RON window: " + ", ".join(rolling_violations),
        },
    ]
    failed = sum(check["status"] == "fail" for check in checks)
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "curfew_safe_topology_repair",
        "planningRulesId": planning_rules["id"],
        "operatingPolicyId": policy["id"],
        "status": "pass" if failed == 0 else "fail",
        "materializationStatus": "pending_bank_alignment",
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
            "plannedLegs": planned_legs,
            "routedLegs": len(legs),
            "configuredAircraft": sum(int(value) for value in fleet_counts.values()),
            "requiredAircraft": len(routes),
            "remainingAircraft": sum(int(value) for value in fleet_counts.values()) - len(routes),
            "aircraftShortfall": capacity_shortfall,
            "curfewViolations": len(curfew_violations),
            "destinationsWithoutRon": len(missing),
            "rollingRonViolations": len(rolling_violations),
            "bankTouchLegs": len(bank_touch_legs),
            "bankAlignedLegs": len(bank_aligned),
        },
        "checks": checks,
        "fleetPlan": fleet_plan,
        "routes": routes,
        "legs": legs,
        "diagnostics": {
            "infeasibleFleets": infeasible_fleets,
            "continuityViolations": continuity_violations,
            "turnViolations": turn_violations,
            "curfewViolations": curfew_violations,
            "missingDestinationRons": missing,
            "rollingRonViolations": rolling_violations,
        },
        "materialization": {
            "status": "pending",
            "checkId": "bank_core_alignment",
            "message": "Fleet-feasible route days must now be retimed into the approved hub-bank cores before canonical Line/Day/Route assignment.",
            "bankTouchLegs": len(bank_touch_legs),
            "currentlyAlignedLegs": len(bank_aligned),
        },
        "limitations": [
            "This repair proves a curfew-safe, RON-aware topology inside the selected fleet; it does not silently add aircraft or change fleet counts.",
            "The route-day clock times are feasibility witnesses. Hub-touching legs are not canonical until every required event is retimed into an approved bank core.",
            "Flight numbers and canonical Line/Day/Route identifiers remain intentionally unassigned until bank materialization passes.",
        ],
    }


def build_routing_repair_plan_from_manifest(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loaded = load_demand_sources_from_manifest(manifest_path, repo_root)
    if loaded["manifest"]["id"] != frequency_plan["demandDataVersion"]:
        raise ValueError("Frequency plan version does not match the repair manifest")
    if bank_plan["planningRulesId"] != loaded["planningRules"]["id"]:
        raise ValueError("Bank plan version does not match the repair manifest")
    return build_routing_repair_plan(
        canonical, frequency_plan, bank_plan, loaded["planningRules"]
    )
