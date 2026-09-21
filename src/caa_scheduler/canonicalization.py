from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from typing import Any

from .bank_placement import TIMEZONE_OFFSETS
from .routing import _connection_wait


ROUTE_DAY_START_MINUTE = 180
MINIMUM_FLIGHT_NUMBER = 1001
ROUTE_NUMBER_STARTS = {
    "CRJ200": 101,
    "CRJ700": 301,
    "CRJ900": 501,
    "MAX9": 701,
}


def sha256_json(value: Any, *, indent: int | None = None) -> str:
    """Hash JSON using the same bytes written by ``write_json``."""
    payload = json.dumps(value, indent=indent, ensure_ascii=False) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clock_text(minute: int) -> str:
    minute %= 1440
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _double_letter(index: int) -> str:
    if not 0 <= index < 26 * 26:
        raise ValueError("CRJ line lettering exceeds the AA-ZZ convention")
    return chr(ord("A") + index // 26) + chr(ord("A") + index % 26)


def _line_assignments(cycles: list[dict[str, Any]]) -> dict[str, str]:
    max9 = [cycle for cycle in cycles if cycle["fleet"] == "MAX9"]
    crj = [cycle for cycle in cycles if cycle["fleet"] != "MAX9"]
    unsupported = sorted(
        {cycle["fleet"] for cycle in crj if not str(cycle["fleet"]).startswith("CRJ")}
    )
    if unsupported:
        raise ValueError(
            "Canonical line lettering needs a convention for: "
            + ", ".join(unsupported)
        )
    if len(max9) > 26:
        raise ValueError("MAX9 line lettering exceeds the A-Z convention")
    assignments = {
        cycle["id"]: chr(ord("A") + index)
        for index, cycle in enumerate(sorted(max9, key=lambda row: row["id"]))
    }
    assignments.update(
        {
            cycle["id"]: _double_letter(index)
            for index, cycle in enumerate(sorted(crj, key=lambda row: row["id"]))
        }
    )
    return assignments


def _unwrapped_departures(
    identifiers: list[str],
    legs: dict[str, dict[str, Any]],
    minimum_turn: int,
) -> list[int]:
    departures = [int(legs[identifiers[0]]["departureUtcMinute"])]
    for previous_id, next_id in zip(identifiers, identifiers[1:]):
        previous = legs[previous_id]
        arrival = departures[-1] + int(previous["blockMinutes"])
        departures.append(
            arrival
            + _connection_wait(
                arrival,
                int(legs[next_id]["departureUtcMinute"]),
                minimum_turn,
            )
        )
    return departures


def _cycle_route_days(
    cycle: dict[str, Any],
    legs: dict[str, dict[str, Any]],
    cities: dict[str, dict[str, Any]],
    minimum_turn: int,
) -> list[tuple[str, int]]:
    identifiers = list(cycle["legIds"])
    if not identifiers:
        raise ValueError(f"{cycle['id']} contains no legs")
    expected_days = int(cycle["aircraftRequired"])
    candidates: list[tuple[tuple[int, str], list[tuple[str, int]]]] = []
    for cut in range(len(identifiers)):
        rotated = identifiers[cut:] + identifiers[:cut]
        departures = _unwrapped_departures(rotated, legs, minimum_turn)
        raw_days = [
            (
                departure
                + TIMEZONE_OFFSETS[cities[legs[identifier]["origin"]]["timezone"]]
                - ROUTE_DAY_START_MINUTE
            )
            // 1440
            for identifier, departure in zip(rotated, departures)
        ]
        first_day = min(raw_days)
        days = [value - first_day + 1 for value in raw_days]
        if days != sorted(days):
            continue
        if sorted(set(days)) != list(range(1, expected_days + 1)):
            continue
        first_leg = legs[rotated[0]]
        candidates.append(
            (
                (
                    (int(first_leg["departureMinute"]) - ROUTE_DAY_START_MINUTE)
                    % 1440,
                    rotated[0],
                ),
                list(zip(rotated, days)),
            )
        )
    if not candidates:
        raise ValueError(
            f"{cycle['id']} cannot be partitioned into {expected_days} "
            "contiguous 03:00-to-03:00 route days"
        )
    return min(candidates, key=lambda row: row[0])[1]


def _pairing_assignments(
    seed: dict[str, Any], generated_legs: list[dict[str, Any]]
) -> tuple[dict[tuple[str, str], int], int]:
    historical: dict[tuple[str, str], set[int]] = defaultdict(set)
    for leg in seed.get("legs", []):
        historical[(leg["origin"], leg["destination"])].add(int(leg["pairing"]))
    ambiguous = sorted(market for market, values in historical.items() if len(values) != 1)
    if ambiguous:
        raise ValueError(
            "The seed schedule has multiple pairing numbers for directed market(s): "
            + ", ".join("-".join(market) for market in ambiguous[:20])
        )
    assignments = {market: next(iter(values)) for market, values in historical.items()}
    used = set(assignments.values())
    next_pairing = max(used, default=100) + 1
    generated_markets = sorted(
        {(leg["origin"], leg["destination"]) for leg in generated_legs}
    )
    reused = 0
    for market in generated_markets:
        if market in assignments:
            reused += 1
            continue
        while next_pairing in used:
            next_pairing += 1
        if next_pairing >= 1000:
            raise ValueError("Pairing numbering exhausted the sub-1000 number space")
        assignments[market] = next_pairing
        used.add(next_pairing)
        next_pairing += 1
    return assignments, reused


def build_canonical_schedule_from_exact_plan(
    seed: dict[str, Any],
    demand_plan: dict[str, Any],
    frequency_plan: dict[str, Any],
    hub_bank_plan: dict[str, Any],
    exact_plan: dict[str, Any],
    construction_provenance: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Assign canonical identifiers to a passing exact materialization plan."""
    schedule_id = str(seed["schedule"]["id"])
    mismatched_schedule_ids = {
        name: str(plan.get("scheduleId"))
        for name, plan in (
            ("frequency plan", frequency_plan),
            ("hub-bank plan", hub_bank_plan),
            ("exact plan", exact_plan),
        )
        if str(plan.get("scheduleId")) != schedule_id
    }
    if mismatched_schedule_ids:
        details = ", ".join(
            f"{name}={identifier}"
            for name, identifier in mismatched_schedule_ids.items()
        )
        raise ValueError(
            f"Canonicalization schedule ID mismatch: seed={schedule_id}; {details}"
        )
    if exact_plan.get("status") != "pass" or exact_plan.get(
        "materializationStatus"
    ) != "complete":
        raise ValueError("Canonicalization requires a complete passing exact plan")
    if hub_bank_plan.get("status") != "pass":
        raise ValueError("Canonicalization requires a passing hub-bank plan")

    exact_legs = {leg["id"]: leg for leg in exact_plan["legs"]}
    cycle_ids = [identifier for cycle in exact_plan["cycles"] for identifier in cycle["legIds"]]
    if len(cycle_ids) != len(set(cycle_ids)) or set(cycle_ids) != set(exact_legs):
        raise ValueError("Exact cycles must cover every exact leg exactly once")

    cities_by_code = {city["code"]: city for city in seed["cities"]}
    minimum_turn = int(seed["operatingPolicy"]["turns"]["minimumMinutes"])
    line_by_cycle = _line_assignments(exact_plan["cycles"])
    route_counters = copy.deepcopy(ROUTE_NUMBER_STARTS)
    generated: list[dict[str, Any]] = []
    line_day_counts: dict[str, int] = {}
    cycle_by_line: dict[str, str] = {}

    for cycle in sorted(exact_plan["cycles"], key=lambda row: row["id"]):
        fleet = str(cycle["fleet"])
        if fleet not in route_counters:
            raise ValueError(f"No canonical route-number block is defined for {fleet}")
        line = line_by_cycle[cycle["id"]]
        cycle_by_line[line] = cycle["id"]
        route_days = _cycle_route_days(
            cycle, exact_legs, cities_by_code, minimum_turn
        )
        line_day_counts[line] = max(day for _, day in route_days)
        sequences: defaultdict[int, int] = defaultdict(int)
        route_by_day: dict[int, int] = {}
        for identifier, day in route_days:
            if day not in route_by_day:
                route_by_day[day] = route_counters[fleet]
                route_counters[fleet] += 1
            sequences[day] += 1
            source = exact_legs[identifier]
            departure_minute = int(source["departureMinute"]) % 1440
            arrival_clock = int(source["arrivalMinute"]) % 1440
            arrival_minute = arrival_clock
            if arrival_minute <= departure_minute:
                arrival_minute += 1440
            generated.append(
                {
                    "id": identifier,
                    "route": route_by_day[day],
                    "line": line,
                    "fleet": fleet,
                    "day": day,
                    "sequenceWithinRoute": sequences[day],
                    "pairing": 0,
                    "flight": 0,
                    "origin": source["origin"],
                    "destination": source["destination"],
                    "departure": _clock_text(departure_minute),
                    "arrival": _clock_text(arrival_clock),
                    "departureMinute": departure_minute,
                    "arrivalMinute": arrival_minute,
                }
            )

    pairings, reused_pairings = _pairing_assignments(seed, generated)
    for leg in generated:
        leg["pairing"] = pairings[(leg["origin"], leg["destination"])]

    demand_by_market = {
        tuple(sorted((market["origin"], market["destination"]))): float(
            market["twoWayDemand"]
        )
        for market in frequency_plan["markets"]
    }
    flight_order = sorted(
        generated,
        key=lambda leg: (
            -demand_by_market[tuple(sorted((leg["origin"], leg["destination"])))],
            leg["pairing"],
            leg["departureMinute"] % 1440,
            leg["line"],
            leg["day"],
            leg["route"],
            leg["sequenceWithinRoute"],
            leg["id"],
        ),
    )
    for offset, leg in enumerate(flight_order):
        leg["flight"] = MINIMUM_FLIGHT_NUMBER + offset

    cities = copy.deepcopy(seed["cities"])
    demand_cities = {
        row["code"]: row
        for row in demand_plan["multiHubAssignments"]["cities"]
    }
    service_assignments = {
        row["code"]: row["serviceAssignments"]
        for row in frequency_plan.get("cityService", [])
        if "serviceAssignments" in row
    }
    for city in cities:
        demand_city = demand_cities.get(city["code"])
        if demand_city is not None:
            city["demandPercentile"] = float(demand_city["percentile"])
            city["hubAssignments"] = list(
                service_assignments.get(
                    city["code"], demand_city["hubAssignments"]
                )
            )

    hub_banks = [
        {
            "id": bank["id"],
            "hub": hub["hub"],
            "startMinute": int(bank["startMinute"]),
            "endMinute": int(bank["endMinute"]),
        }
        for hub in hub_bank_plan["hubs"]
        for bank in hub["banks"]
    ]
    bank_assignments = []
    for leg in exact_plan["legs"]:
        if leg.get("destinationBankId") is not None:
            bank_assignments.append(
                {
                    "legId": leg["id"],
                    "operation": "arrival",
                    "bankId": leg["destinationBankId"],
                }
            )
        if leg.get("originBankId") is not None:
            bank_assignments.append(
                {
                    "legId": leg["id"],
                    "operation": "departure",
                    "bankId": leg["originBankId"],
                }
            )
    bank_assignments.sort(
        key=lambda row: (row["legId"], row["operation"], row["bankId"])
    )

    provenance = {
        "construction": copy.deepcopy(construction_provenance),
        "cityInformation": copy.deepcopy(seed["provenance"]["cityInformation"]),
        "operatingPolicy": copy.deepcopy(seed["provenance"]["operatingPolicy"]),
    }
    operating_policy = copy.deepcopy(seed["operatingPolicy"])
    effective_bank_counts = {
        hub["hub"]: int(hub["bankCount"])
        for hub in hub_bank_plan["hubs"]
    }
    operating_policy["hubBankCounts"] = effective_bank_counts
    canonical = {
        "schemaVersion": "1.0.0",
        "schedule": copy.deepcopy(seed["schedule"]),
        "provenance": provenance,
        "gatePlan": {
            "label": seed["schedule"]["label"],
            "forcedStandSplits": {},
            "fixedPhysicalInventory": bool(
                seed.get("gatePlan", {}).get("fixedPhysicalInventory", False)
            ),
        },
        "operatingPolicy": operating_policy,
        "hubBanks": hub_banks,
        "bankAssignments": bank_assignments,
        "cities": cities,
        "legs": sorted(generated, key=lambda leg: leg["flight"]),
    }
    report = {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "status": "pass",
        "sourceExactPlanSha256": construction_provenance["exactMaterialization"][
            "sha256"
        ],
        "summary": {
            "cycles": len(exact_plan["cycles"]),
            "lines": len(line_day_counts),
            "routes": len({leg["route"] for leg in generated}),
            "legs": len(generated),
            "pairings": len(
                {(leg["origin"], leg["destination"]) for leg in generated}
            ),
            "reusedPairings": reused_pairings,
            "newPairings": len(
                {(leg["origin"], leg["destination"]) for leg in generated}
            )
            - reused_pairings,
            "bankAssignments": len(bank_assignments),
        },
        "lineDays": dict(sorted(line_day_counts.items())),
        "cycleByLine": dict(sorted(cycle_by_line.items())),
        "numbering": {
            "flightRange": [
                MINIMUM_FLIGHT_NUMBER,
                MINIMUM_FLIGHT_NUMBER + len(generated) - 1,
            ],
            "routeRanges": {
                fleet: [start, route_counters[fleet] - 1]
                for fleet, start in ROUTE_NUMBER_STARTS.items()
            },
        },
    }
    return canonical, report
