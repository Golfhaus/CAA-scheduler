from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from .bank_placement import _curfew_status, _local_arrival
from .demand import load_demand_sources_from_manifest
from .routing import _local_minute, _ron_count, _utc_minute
from .routing_repair import _leg_inventory


def _bank_options(
    leg_type: dict[str, Any],
    windows: dict[str, list[dict[str, Any]]],
    hubs: set[str],
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    origin = leg_type["origin"]
    destination = leg_type["destination"]
    block = int(leg_type["blockMinutes"])
    option_departures: list[list[int]] = []
    if origin in hubs and destination in hubs:
        for origin_bank in windows[origin]:
            for destination_bank in windows[destination]:
                departures = []
                for departure in range(
                    int(origin_bank["startMinute"]),
                    int(origin_bank["endMinute"]),
                    5,
                ):
                    arrival = _local_arrival(
                        departure, block, origin, destination, cities
                    )
                    if not (
                        int(destination_bank["startMinute"])
                        <= arrival
                        < int(destination_bank["endMinute"])
                    ):
                        continue
                    if _curfew_status(
                        origin, departure, arrival, policy
                    ) == "pass":
                        departures.append(_utc_minute(departure, origin, cities))
                if departures:
                    option_departures.append(departures)
    elif origin in hubs:
        for bank in windows[origin]:
            departures = []
            for departure in range(
                int(bank["startMinute"]), int(bank["endMinute"]), 5
            ):
                arrival = _local_arrival(
                    departure, block, origin, destination, cities
                )
                if _curfew_status(origin, departure, arrival, policy) == "pass":
                    departures.append(_utc_minute(departure, origin, cities))
            if departures:
                option_departures.append(departures)
    else:
        for bank in windows[destination]:
            departures = []
            for arrival in range(
                int(bank["startMinute"]), int(bank["endMinute"]), 5
            ):
                arrival_utc = _utc_minute(arrival, destination, cities)
                departure_utc = (arrival_utc - block) % 1440
                departure = _local_minute(departure_utc, origin, cities)
                if _curfew_status(origin, departure, arrival, policy) == "pass":
                    departures.append(departure_utc)
            if departures:
                option_departures.append(departures)
    options = []
    for departures in option_departures:
        departure_minutes = tuple(sorted(set(departures)))
        arrival_minutes = tuple(
            sorted({(minute + block) % 1440 for minute in departure_minutes})
        )
        options.append(
            {
                "departureUtcMinutes": departure_minutes,
                "arrivalUtcMinutes": arrival_minutes,
            }
        )
    return sorted(
        {
            (row["departureUtcMinutes"], row["arrivalUtcMinutes"]): row
            for row in options
        }.values(),
        key=lambda row: (
            row["departureUtcMinutes"][0],
            row["arrivalUtcMinutes"][0],
        ),
    )


def _banked_leg_types(
    frequency_plan: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    cities: dict[str, dict[str, Any]],
    bank_plan: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    hubs = set(policy["hubs"])
    windows = {row["hub"]: row["banks"] for row in bank_plan["hubs"]}
    inventory = _leg_inventory(frequency_plan, profiles, cities)
    grouped: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    nonhub_count = 0
    for fleet_legs in inventory.values():
        for leg in fleet_legs:
            if leg["origin"] not in hubs and leg["destination"] not in hubs:
                nonhub_count += 1
                continue
            grouped[
                (
                    leg["fleet"],
                    leg["origin"],
                    leg["destination"],
                    leg["classification"],
                    int(leg["blockMinutes"]),
                )
            ].append(leg)

    leg_types = []
    for key, legs in sorted(grouped.items()):
        fleet, origin, destination, classification, block = key
        row = {
            "key": key,
            "fleet": fleet,
            "origin": origin,
            "destination": destination,
            "classification": classification,
            "blockMinutes": block,
            "count": len(legs),
        }
        row["options"] = _bank_options(row, windows, hubs, cities, policy)
        if not row["options"]:
            raise ValueError(
                f"No curfew-safe bank-core option exists for "
                f"{origin}-{destination}-{fleet}"
            )
        leg_types.append(row)
    return leg_types, nonhub_count


def _solve_flow_lower_bound(
    leg_types: list[dict[str, Any]],
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    *,
    require_destination_rons: bool,
) -> dict[str, Any]:
    minimum_turn = int(policy["turns"]["minimumMinutes"])
    y_variables = [
        (type_index, leg_type, option)
        for type_index, leg_type in enumerate(leg_types)
        for option in leg_type["options"]
    ]
    arrival_times: defaultdict[tuple[str, str], set[tuple[int, ...]]] = defaultdict(set)
    departure_times: defaultdict[tuple[str, str], set[tuple[int, ...]]] = defaultdict(set)
    y_by_type: defaultdict[int, list[int]] = defaultdict(list)
    y_by_arrival: defaultdict[tuple[str, str, int], list[int]] = defaultdict(list)
    y_by_departure: defaultdict[tuple[str, str, int], list[int]] = defaultdict(list)
    for index, (type_index, leg_type, option) in enumerate(y_variables):
        departure_event = tuple(option["departureUtcMinutes"])
        arrival_event = tuple(option["arrivalUtcMinutes"])
        y_by_type[type_index].append(index)
        y_by_departure[
            (leg_type["origin"], leg_type["fleet"], departure_event)
        ].append(index)
        y_by_arrival[
            (leg_type["destination"], leg_type["fleet"], arrival_event)
        ].append(index)
        departure_times[(leg_type["origin"], leg_type["fleet"])].add(
            departure_event
        )
        arrival_times[(leg_type["destination"], leg_type["fleet"])].add(
            arrival_event
        )

    z_variables = []
    station_fleets = sorted(set(arrival_times) | set(departure_times))
    for station, fleet in station_fleets:
        for arrival_event in sorted(arrival_times[(station, fleet)]):
            for departure_event in sorted(departure_times[(station, fleet)]):
                waits = []
                ron_possible = False
                for arrival_utc in arrival_event:
                    for departure_utc in departure_event:
                        wait = (departure_utc - arrival_utc) % 1440
                        if wait < minimum_turn:
                            wait += 1440
                        waits.append(wait)
                        ron_possible = ron_possible or bool(
                            _ron_count(
                                arrival_utc,
                                arrival_utc + wait,
                                station,
                                cities,
                            )
                        )
                z_variables.append(
                    (
                        station,
                        fleet,
                        arrival_event,
                        departure_event,
                        min(waits),
                        ron_possible,
                    )
                )

    y_count = len(y_variables)
    z_by_arrival: defaultdict[tuple[str, str, int], list[int]] = defaultdict(list)
    z_by_departure: defaultdict[tuple[str, str, int], list[int]] = defaultdict(list)
    z_by_station: defaultdict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(z_variables, y_count):
        station, fleet, arrival_event, departure_event, _, _ = candidate
        z_by_arrival[(station, fleet, arrival_event)].append(index)
        z_by_departure[(station, fleet, departure_event)].append(index)
        z_by_station[station].append(index)
    equality_rows: list[dict[int, float]] = []
    equality_values = []
    for type_index, leg_type in enumerate(leg_types):
        equality_rows.append({index: 1.0 for index in y_by_type[type_index]})
        equality_values.append(float(leg_type["count"]))

    for station, fleet in station_fleets:
        for arrival_event in sorted(arrival_times[(station, fleet)]):
            key = (station, fleet, arrival_event)
            row = {index: -1.0 for index in y_by_arrival[key]}
            row.update({index: 1.0 for index in z_by_arrival[key]})
            equality_rows.append(row)
            equality_values.append(0.0)
        for departure_event in sorted(departure_times[(station, fleet)]):
            key = (station, fleet, departure_event)
            row = {index: -1.0 for index in y_by_departure[key]}
            row.update({index: 1.0 for index in z_by_departure[key]})
            equality_rows.append(row)
            equality_values.append(0.0)

    inequality_rows: list[dict[int, float]] = []
    inequality_values = []
    ron_destinations = []
    if require_destination_rons:
        exemptions = set(policy.get("destinationRonExemptions", []))
        for destination in sorted(
            city["code"]
            for city in cities.values()
            if city["role"] == "destination" and city["code"] not in exemptions
        ):
            row = {}
            for index in z_by_station[destination]:
                candidate = z_variables[index - y_count]
                station, _, _, _, _, ron_possible = candidate
                if station == destination and ron_possible:
                    row[index] = -1.0
            if not row:
                raise ValueError(
                    f"No banked connection can provide the required RON at {destination}"
                )
            inequality_rows.append(row)
            inequality_values.append(-1.0)
            ron_destinations.append(destination)

    def sparse_matrix(rows: list[dict[int, float]]) -> Any:
        matrix_rows = []
        matrix_columns = []
        matrix_values = []
        for row_index, row in enumerate(rows):
            for column_index, value in row.items():
                matrix_rows.append(row_index)
                matrix_columns.append(column_index)
                matrix_values.append(value)
        return coo_matrix(
            (matrix_values, (matrix_rows, matrix_columns)),
            shape=(len(rows), y_count + len(z_variables)),
        ).tocsr()

    objective = np.zeros(y_count + len(z_variables))
    for index, candidate in enumerate(z_variables, y_count):
        objective[index] = float(candidate[4])
    result = linprog(
        objective,
        A_ub=sparse_matrix(inequality_rows) if inequality_rows else None,
        b_ub=np.array(inequality_values) if inequality_rows else None,
        A_eq=sparse_matrix(equality_rows),
        b_eq=np.array(equality_values),
        bounds=(0, None),
        method="highs",
    )
    if not result.success or result.x is None:
        raise ValueError(f"Bank-flow lower-bound solve failed: {result.message}")

    block_by_fleet: defaultdict[str, int] = defaultdict(int)
    for leg_type in leg_types:
        block_by_fleet[leg_type["fleet"]] += (
            int(leg_type["blockMinutes"]) * int(leg_type["count"])
        )
    fleet_rows = {}
    for fleet in sorted(block_by_fleet):
        wait = sum(
            float(value) * int(candidate[4])
            for value, candidate in zip(result.x[y_count:], z_variables)
            if candidate[1] == fleet
        )
        total = block_by_fleet[fleet] + wait
        fleet_rows[fleet] = {
            "bankedBlockMinutes": block_by_fleet[fleet],
            "minimumConnectionWaitMinutes": round(wait, 6),
            "minimumAircraftMinutes": round(total, 6),
            "minimumAircraftDays": round(total / 1440, 6),
            "minimumWholeAircraft": math.ceil(total / 1440 - 1e-9),
        }
    return {
        "solver": "scipy-highs-bank-window-relaxation",
        "objectiveMinutes": round(float(result.fun), 6),
        "legTypes": len(leg_types),
        "bankOptionVariables": y_count,
        "connectionVariables": len(z_variables),
        "destinationRonConstraints": len(ron_destinations),
        "fleet": fleet_rows,
    }


def build_bank_materialization_diagnostic(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    planning_rules: dict[str, Any],
) -> dict[str, Any]:
    if frequency_plan.get("status") != "pass" or bank_plan.get("status") != "pass":
        raise ValueError(
            "Bank materialization requires passing frequency and bank plans"
        )
    cities = {
        city["code"]: city for city in canonical["cities"] if city.get("active")
    }
    policy = canonical["operatingPolicy"]
    profiles = {
        row["fleet"]: row
        for row in planning_rules["frequencyAllocation"]["fleetProfiles"]
    }
    leg_types, nonhub_legs = _banked_leg_types(
        frequency_plan, profiles, cities, bank_plan, policy
    )
    base = _solve_flow_lower_bound(
        leg_types, cities, policy, require_destination_rons=False
    )
    ron = _solve_flow_lower_bound(
        leg_types, cities, policy, require_destination_rons=True
    )
    fleet_counts = canonical["schedule"]["fleetCounts"]
    fleet_plan = {}
    for fleet, configured in fleet_counts.items():
        base_row = base["fleet"][fleet]
        ron_row = ron["fleet"][fleet]
        minimum = int(ron_row["minimumWholeAircraft"])
        shortfall = max(0, minimum - int(configured))
        fleet_plan[fleet] = {
            "configuredAircraft": int(configured),
            "bankOnlyMinimumAircraft": int(base_row["minimumWholeAircraft"]),
            "bankAndRonMinimumAircraft": minimum,
            "minimumAircraftDays": ron_row["minimumAircraftDays"],
            "minimumAircraftMinutes": ron_row["minimumAircraftMinutes"],
            "shortfall": shortfall,
            "headroom": max(0, int(configured) - minimum),
        }
    shortfall = sum(row["shortfall"] for row in fleet_plan.values())
    configured_total = sum(int(value) for value in fleet_counts.values())
    minimum_total = sum(
        row["bankAndRonMinimumAircraft"] for row in fleet_plan.values()
    )
    banked_legs = sum(int(row["count"]) for row in leg_types)
    checks = [
        {
            "id": "directional_bank_assignment",
            "status": "pass",
            "message": (
                "Inbound and outbound market frequencies are independently assigned "
                "to approved bank cores before aircraft routing"
            ),
        },
        {
            "id": "banked_service_coverage",
            "status": "pass"
            if banked_legs == int(bank_plan["summary"]["hubMarketLegs"])
            else "fail",
            "message": f"All {banked_legs} hub-touching legs enter the time-flow model",
        },
        {
            "id": "curfew_enforcement",
            "status": "pass",
            "hardStop": True,
            "message": "Every eligible bank option passes the hard curfew rules",
        },
        {
            "id": "destination_ron_lower_bound",
            "status": "pass",
            "message": (
                f"The relaxed flow reserves a RON-capable connection at all "
                f"{ron['destinationRonConstraints']} required destinations"
            ),
        },
        {
            "id": "fleet_allocation_fit",
            "status": "fail" if shortfall else "pass",
            "message": (
                "The bank-window lower bound remains within every configured fleet"
                if not shortfall
                else "Even the bank-window lower bound exceeds the configured allocation for: "
                + ", ".join(
                    f"{fleet} ({row['bankAndRonMinimumAircraft']}/"
                    f"{row['configuredAircraft']})"
                    for fleet, row in fleet_plan.items()
                    if row["shortfall"]
                )
            ),
        },
        {
            "id": "nonhub_materialization",
            "status": "pending",
            "message": (
                f"{nonhub_legs} non-hub legs remain to be inserted after fleet "
                "allocation repair"
            ),
        },
    ]
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "independent_direction_bank_flow_lower_bound",
        "planningRulesId": planning_rules["id"],
        "operatingPolicyId": policy["id"],
        "directionalBankAssignment": "independent",
        "bankWindowTiming": "full_core_five_minute_options",
        "status": "blocked_fleet_allocation" if shortfall else "pending_nonhub_integration",
        "materializationStatus": "blocked" if shortfall else "pending",
        "summary": {
            "bankedLegs": banked_legs,
            "nonHubLegs": nonhub_legs,
            "configuredAircraft": configured_total,
            "bankAndRonMinimumAircraft": minimum_total,
            "fleetAllocationShortfall": shortfall,
            "bankWindowLowerBoundHeadroom": sum(
                row["headroom"] for row in fleet_plan.values()
            ),
            "curfewViolations": 0,
            "requiredDestinationRons": ron["destinationRonConstraints"],
        },
        "checks": checks,
        "fleetPlan": fleet_plan,
        "lowerBounds": {
            "withoutDestinationRon": base,
            "withDestinationRon": ron,
        },
        "nextRepair": {
            "status": "requires_policy_confirmation" if shortfall else "ready",
            "action": "compatible_fleet_reassignment" if shortfall else "integrate_nonhub_legs",
            "message": (
                "Reassign the smallest compatible set of CRJ200 markets into "
                "available larger-fleet capacity without changing schedule fleet counts."
                if shortfall
                else f"Integrate all {nonhub_legs} non-hub legs, then solve exact whole-flight route cycles."
            ),
        },
        "limitations": [
            "This continuous bank-window relaxation is a mathematical lower bound, not a published timetable; if it exceeds a fleet count, no integer routing can fit that allocation.",
            "The relaxation may select different five-minute points inside the same event window for different connections, so fitting the lower bound does not prove that exact whole-flight route cycles exist.",
            "The diagnostic preserves the schedule-selected fleet counts and does not silently add aircraft.",
            "Canonical Line/Day/Route, pairing, and flight identifiers remain unassigned until exact materialization passes.",
        ],
    }


def build_bank_materialization_diagnostic_from_manifest(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    bank_plan: dict[str, Any],
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loaded = load_demand_sources_from_manifest(manifest_path, repo_root)
    if loaded["manifest"]["id"] != frequency_plan["demandDataVersion"]:
        raise ValueError(
            "Frequency plan version does not match the materialization manifest"
        )
    if bank_plan["planningRulesId"] != loaded["planningRules"]["id"]:
        raise ValueError(
            "Bank plan version does not match the materialization manifest"
        )
    return build_bank_materialization_diagnostic(
        canonical,
        frequency_plan,
        bank_plan,
        loaded["planningRules"],
    )
