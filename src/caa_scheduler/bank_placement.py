from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .demand import load_demand_sources_from_manifest
from .gate_export import _capacity
from .planning import haversine_nm


TIMEZONE_OFFSETS = {
    "Eastern": -300,
    "Central": -360,
    "Mountain": -420,
    "Pacific": -480,
}


def _block_minutes(
    origin: str,
    destination: str,
    profile: dict[str, Any],
    cities: dict[str, dict[str, Any]],
) -> int:
    distance = haversine_nm(
        float(cities[origin]["latitude"]),
        float(cities[origin]["longitude"]),
        float(cities[destination]["latitude"]),
        float(cities[destination]["longitude"]),
    )
    return round(
        float(profile["blockMinutesPerNauticalMile"]) * distance
        + float(profile["blockMinutesIntercept"])
    )


def _local_arrival(
    departure: int,
    block: int,
    origin: str,
    destination: str,
    cities: dict[str, dict[str, Any]],
) -> int:
    origin_offset = TIMEZONE_OFFSETS[cities[origin]["timezone"]]
    destination_offset = TIMEZONE_OFFSETS[cities[destination]["timezone"]]
    return (departure + block + destination_offset - origin_offset) % 1440


def _local_departure(
    arrival: int,
    block: int,
    origin: str,
    destination: str,
    cities: dict[str, dict[str, Any]],
) -> int:
    origin_offset = TIMEZONE_OFFSETS[cities[origin]["timezone"]]
    destination_offset = TIMEZONE_OFFSETS[cities[destination]["timezone"]]
    return (arrival - block - destination_offset + origin_offset) % 1440


def _curfew_status(
    origin: str,
    departure: int,
    arrival: int,
    policy: dict[str, Any],
) -> str:
    windows = policy["departureWindows"]
    hubs_or_focus = set(policy["hubs"]) | set(policy["focusCities"])
    latest = (
        windows["hubOrFocusLatestMinute"]
        if origin in hubs_or_focus
        else windows["destinationLatestMinute"]
    )
    normal = windows["earliestMinute"] <= departure <= latest
    red_eye = (
        (
            departure > windows["destinationLatestMinute"]
            or departure <= windows["redEyeLatestMinute"]
        )
        and windows["redEyeArrivalMinimumMinute"]
        <= arrival
        <= windows["redEyeArrivalMaximumMinute"]
    )
    return "pass" if normal or red_eye else "fail"


def _starts(
    hub: str,
    phase: dict[str, int],
    bank_counts: dict[str, int],
    cadence_by_count: dict[str, int],
) -> list[int]:
    cadence = int(cadence_by_count[str(bank_counts[hub])])
    return [phase[hub] + index * cadence for index in range(bank_counts[hub])]


def _interhub_candidates(
    origin: str,
    destination: str,
    block: int,
    windows: dict[str, list[dict[str, Any]]],
    cities: dict[str, dict[str, Any]],
    step: int,
) -> list[tuple[dict[str, Any], dict[str, Any], int, int]]:
    candidates = []
    for origin_bank in windows[origin]:
        for departure in range(
            origin_bank["startMinute"], origin_bank["endMinute"], step
        ):
            arrival = _local_arrival(
                departure, block, origin, destination, cities
            )
            for destination_bank in windows[destination]:
                if (
                    destination_bank["startMinute"]
                    <= arrival
                    < destination_bank["endMinute"]
                ):
                    candidates.append(
                        (origin_bank, destination_bank, departure, arrival)
                    )
    return candidates


def _has_interhub_candidate(
    origin: str,
    destination: str,
    block: int,
    windows: dict[str, list[dict[str, Any]]],
    cities: dict[str, dict[str, Any]],
    step: int,
) -> bool:
    return bool(
        _interhub_candidates(
            origin,
            destination,
            block,
            windows,
            cities,
            step,
        )
    )


def _maximum_spaced_departures(
    departures: set[int], minimum_gap: int
) -> int:
    """Return the maximum cyclic selection at or above ``minimum_gap``."""
    if not departures:
        return 0
    best = 0
    for first in sorted(departures):
        offsets = sorted((minute - first) % 1440 for minute in departures)
        selected: list[int] = []
        for offset in offsets:
            if not selected or offset - selected[-1] >= minimum_gap:
                selected.append(offset)
        while (
            len(selected) > 1
            and 1440 - selected[-1] + selected[0] < minimum_gap
        ):
            selected.pop()
        best = max(best, len(selected))
    return best


def _nearest_cyclic_gap(minute: int, assigned: list[int]) -> int:
    """Return the nearest circular gap to an already assigned departure."""
    if not assigned:
        return 1440
    return min(
        min((minute - other) % 1440, (other - minute) % 1440)
        for other in assigned
    )


def _interhub_spacing_capacity(
    services: list[dict[str, Any]],
    windows: dict[str, list[dict[str, Any]]],
    cities: dict[str, dict[str, Any]],
    step: int,
    minimum_gap: int,
) -> list[dict[str, Any]]:
    grouped: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for service in services:
        grouped[(service["origin"], service["destination"])].append(service)
    rows = []
    for (origin, destination), pairing_services in sorted(grouped.items()):
        departures = {
            candidate[2]
            for service in pairing_services
            for candidate in _interhub_candidates(
                origin,
                destination,
                service["blockMinutes"],
                windows,
                cities,
                step,
            )
        }
        required = sum(int(service["weight"]) for service in pairing_services)
        capacity = _maximum_spaced_departures(departures, minimum_gap)
        rows.append(
            {
                "origin": origin,
                "destination": destination,
                "requiredDepartures": required,
                "spacedCandidateCapacity": capacity,
                "shortfall": max(0, required - capacity),
            }
        )
    return rows


def _optimize_phases(
    hubs: list[str],
    interhub_services: list[dict[str, Any]],
    spoke_services: list[dict[str, Any]],
    bank_counts: dict[str, int],
    bank_rules: dict[str, Any],
    cities: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, int]:
    earliest = int(bank_rules["phaseCandidateEarliestMinute"])
    latest = int(bank_rules["phaseCandidateLatestMinute"])
    phase_step = int(bank_rules["phaseStepMinutes"])
    candidates = list(range(earliest, latest + 1, phase_step))
    cadence = bank_rules["cadenceMinutesByBankCount"]
    width = 60

    def windows_for(phase: dict[str, int]) -> dict[str, list[dict[str, Any]]]:
        return {
            hub: [
                {
                    "id": f"{hub}-B{index + 1}",
                    "startMinute": start,
                    "endMinute": start + width,
                }
                for index, start in enumerate(
                    _starts(hub, phase, bank_counts, cadence)
                )
            ]
            for hub in hubs
        }

    def score(phase: dict[str, int]) -> tuple[int, ...]:
        windows = windows_for(phase)
        directional_banks = 0
        if bank_rules.get("requireDirectionalPhaseCoverage", False):
            for hub in hubs:
                hub_services = [
                    service for service in spoke_services if service["hub"] == hub
                ]
                for bank in windows[hub]:
                    arrival_target = (
                        bank["startMinute"]
                        + int(bank_rules["spokeArrivalOffsetMinutes"])
                    )
                    departure_target = (
                        bank["startMinute"]
                        + int(bank_rules["hubDepartureOffsetMinutes"])
                    )
                    if any(
                        _curfew_status(
                            service["spoke"],
                            _local_departure(
                                arrival_target,
                                service["blockMinutes"],
                                service["spoke"],
                                hub,
                                cities,
                            ),
                            arrival_target,
                            policy,
                        )
                        == "pass"
                        and _curfew_status(
                            hub,
                            departure_target,
                            _local_arrival(
                                departure_target,
                                service["blockMinutes"],
                                hub,
                                service["spoke"],
                                cities,
                            ),
                            policy,
                        )
                        == "pass"
                        for service in hub_services
                    ):
                        directional_banks += 1
        spoke_capacity_score: tuple[int, int] = (0, 0)
        if bank_rules.get("optimizeSpokePlacementCapacity", False):
            spoke_shortfall = 0
            spoke_covered = 0
            for service in spoke_services:
                feasible_banks = sum(
                    1
                    for bank in windows[service["hub"]]
                    if (
                        _curfew_status(
                            service["spoke"],
                            _local_departure(
                                bank["startMinute"]
                                + int(bank_rules["spokeArrivalOffsetMinutes"]),
                                service["blockMinutes"],
                                service["spoke"],
                                service["hub"],
                                cities,
                            ),
                            bank["startMinute"]
                            + int(bank_rules["spokeArrivalOffsetMinutes"]),
                            policy,
                        )
                        == "pass"
                        and _curfew_status(
                            service["hub"],
                            bank["startMinute"]
                            + int(bank_rules["hubDepartureOffsetMinutes"]),
                            _local_arrival(
                                bank["startMinute"]
                                + int(bank_rules["hubDepartureOffsetMinutes"]),
                                service["blockMinutes"],
                                service["hub"],
                                service["spoke"],
                                cities,
                            ),
                            policy,
                        )
                        == "pass"
                    )
                )
                required = int(service["weight"])
                spoke_shortfall += max(0, required - feasible_banks)
                spoke_covered += min(required, feasible_banks)
            spoke_capacity_score = (-spoke_shortfall, spoke_covered)
        if bank_rules.get("requireInterhubSpacingCapacity", False):
            capacity_rows = _interhub_spacing_capacity(
                interhub_services,
                windows,
                cities,
                int(bank_rules["interHubSearchStepMinutes"]),
                int(policy["section26"]["hardFloorMinutes"]),
            )
            shortfall = sum(row["shortfall"] for row in capacity_rows)
            covered = sum(
                min(row["requiredDepartures"], row["spacedCandidateCapacity"])
                for row in capacity_rows
            )
            return (
                *spoke_capacity_score,
                directional_banks,
                -shortfall,
                covered,
            )
        interhub_score = sum(
            service["weight"]
            for service in interhub_services
            if _has_interhub_candidate(
                service["origin"],
                service["destination"],
                service["blockMinutes"],
                windows,
                cities,
                int(bank_rules["interHubSearchStepMinutes"]),
            )
        )
        return (*spoke_capacity_score, directional_banks, interhub_score)

    best: tuple[tuple[int, ...], tuple[int, ...], dict[str, int]] | None = None
    for seed in candidates:
        phase = {hub: seed for hub in hubs}
        for _ in range(10):
            changed = False
            for hub in hubs:
                prior = phase[hub]
                choices = []
                for value in candidates:
                    phase[hub] = value
                    choices.append((*score(phase), -abs(value - prior), -value, value))
                chosen = max(choices)[-1]
                phase[hub] = chosen
                changed = changed or chosen != prior
            if not changed:
                break
        result = (score(phase), tuple(-phase[hub] for hub in hubs), dict(phase))
        if best is None or result[:2] > best[:2]:
            best = result
    if best is None:
        raise ValueError("Hub-bank phase search has no candidate phases")
    return best[2]


def build_hub_bank_plan(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    planning_rules: dict[str, Any],
) -> dict[str, Any]:
    """Place proposed hub-touching service into generated bank windows.

    The result is deliberately independent from canonical legs. It establishes
    curfew-safe local clock times for proposed hub flying while aircraft routing
    remains a downstream construction step.
    """
    if frequency_plan.get("status") != "pass":
        raise ValueError("Hub-bank placement requires a passing frequency/fleet plan")
    bank_rules = planning_rules["bankPlacement"]
    distinct_pairing_waves = bool(
        bank_rules.get(
            "requireDistinctPairingWaves",
            planning_rules.get("exactMaterialization", {}).get(
                "preserveAssignedBankWaves", False
            ),
        )
    )
    prefer_pairing_spread = bool(
        bank_rules.get("preferPairingSpread", distinct_pairing_waves)
    )
    enforce_gate_capacity = bool(
        planning_rules["frequencyAllocation"].get(
            "enforceHubGateBankThroughput", False
        )
    )
    policy = canonical["operatingPolicy"]
    hubs = sorted(policy["hubs"])
    hub_set = set(hubs)
    policy_bank_counts = policy["hubBankCounts"]
    bank_counts = bank_rules.get("hubBankCountsOverride", policy_bank_counts)
    if set(bank_counts) != set(hubs):
        raise ValueError(
            "Effective hub-bank counts must define every operating-policy hub"
        )
    width = int(policy["hubBankWindowMinutes"])
    if width != 60:
        raise ValueError("The v1 bank placer requires the policy's 60-minute core")
    cities = {
        city["code"]: city for city in canonical["cities"] if city.get("active")
    }
    hub_gate_counts = {hub: _capacity(cities[hub])[0] for hub in hubs}
    for city in cities.values():
        timezone = city.get("timezone")
        if timezone not in TIMEZONE_OFFSETS:
            raise ValueError(f"Bank placement has no UTC offset for {timezone!r}")
    profiles = {
        row["fleet"]: row
        for row in planning_rules["frequencyAllocation"]["fleetProfiles"]
    }

    interhub_services = []
    spoke_services = []
    for market in frequency_plan["markets"]:
        market_hubs = [
            code
            for code in (market["origin"], market["destination"])
            if code in hub_set
        ]
        if not market_hubs:
            continue
        for allocation in market["allocations"]:
            block = _block_minutes(
                market["origin"], market["destination"],
                profiles[allocation["fleet"]], cities,
            )
            if len(market_hubs) == 1:
                hub = market_hubs[0]
                spoke = (
                    market["destination"]
                    if market["origin"] == hub
                    else market["origin"]
                )
                spoke_services.append(
                    {
                        "hub": hub,
                        "spoke": spoke,
                        "blockMinutes": block,
                        "weight": allocation["roundTrips"],
                    }
                )
                continue
            for origin, destination in (
                (market["origin"], market["destination"]),
                (market["destination"], market["origin"]),
            ):
                interhub_services.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "fleet": allocation["fleet"],
                        "blockMinutes": block,
                        "weight": allocation["roundTrips"],
                    }
                )

    phase = _optimize_phases(
        hubs,
        interhub_services,
        spoke_services,
        bank_counts,
        bank_rules,
        cities,
        policy,
    )
    windows: dict[str, list[dict[str, Any]]] = {}
    for hub in hubs:
        starts = _starts(
            hub, phase, bank_counts, bank_rules["cadenceMinutesByBankCount"]
        )
        windows[hub] = [
            {
                "id": f"{hub}-B{index + 1}",
                "sequence": index + 1,
                "startMinute": start,
                "endMinute": start + width,
                "arrivalTargetMinute": start
                + int(bank_rules["spokeArrivalOffsetMinutes"]),
                "departureTargetMinute": start
                + int(bank_rules["hubDepartureOffsetMinutes"]),
            }
            for index, start in enumerate(starts)
        ]

    touch_load: Counter[tuple[str, str]] = Counter()
    pairing_wave_load: Counter[tuple[str, str, str]] = Counter()
    pairing_departure_minutes: defaultdict[
        tuple[str, str], list[int]
    ] = defaultdict(list)
    placements: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []

    def add_leg(
        *,
        identifier: str,
        market: dict[str, Any],
        fleet: str,
        ordinal: int,
        direction: str,
        origin: str,
        destination: str,
        departure: int,
        arrival: int,
        block: int,
        touches: list[dict[str, str]],
    ) -> None:
        status = _curfew_status(origin, departure, arrival, policy)
        for touch in touches:
            touch_load[(touch["bankId"], touch["operation"])] += 1
        timing_wave = next(
            (
                touch["bankId"]
                for touch in touches
                if touch["operation"] == "departure"
            ),
            touches[0]["bankId"],
        )
        pairing_wave_load[(origin, destination, timing_wave)] += 1
        pairing_departure_minutes[(origin, destination)].append(departure)
        placements.append(
            {
                "id": identifier,
                "market": [market["origin"], market["destination"]],
                "classification": market["classification"],
                "fleet": fleet,
                "roundTripOrdinal": ordinal,
                "direction": direction,
                "origin": origin,
                "destination": destination,
                "departureMinute": departure,
                "arrivalMinute": arrival,
                "blockMinutes": block,
                "bankTouches": touches,
                "curfewStatus": status,
            }
        )

    placement_markets: list[dict[str, Any]]
    if bank_rules.get("prioritizeMandatoryService", False):
        mandatory_parts = []
        optional_parts = []
        for market in frequency_plan["markets"]:
            remaining_mandatory = int(market["mandatoryRoundTrips"])
            ordinal_offset = 0
            for allocation in market["allocations"]:
                total = int(allocation["roundTrips"])
                mandatory = min(total, remaining_mandatory)
                optional = total - mandatory
                if mandatory:
                    mandatory_parts.append(
                        {
                            **market,
                            "allocations": [
                                {**allocation, "roundTrips": mandatory}
                            ],
                            "_ordinalOffset": ordinal_offset,
                        }
                    )
                if optional:
                    optional_parts.append(
                        {
                            **market,
                            "allocations": [
                                {**allocation, "roundTrips": optional}
                            ],
                            "_ordinalOffset": ordinal_offset + mandatory,
                        }
                    )
                remaining_mandatory -= mandatory
                ordinal_offset += total
        placement_markets = [
            *sorted(
                mandatory_parts,
                key=lambda row: (
                    -row["twoWayDemand"],
                    row["origin"],
                    row["destination"],
                    row["_ordinalOffset"],
                ),
            ),
            *sorted(
                optional_parts,
                key=lambda row: (
                    -row["twoWayDemand"],
                    row["origin"],
                    row["destination"],
                    row["_ordinalOffset"],
                ),
            ),
        ]
    else:
        placement_markets = sorted(
            frequency_plan["markets"],
            key=lambda row: (
                -row["twoWayDemand"],
                row["origin"],
                row["destination"],
            ),
        )

    for market in placement_markets:
        market_hubs = [
            code
            for code in (market["origin"], market["destination"])
            if code in hub_set
        ]
        if not market_hubs:
            continue
        ordinal = int(market.get("_ordinalOffset", 0))
        for allocation in market["allocations"]:
            fleet = allocation["fleet"]
            block = _block_minutes(
                market["origin"], market["destination"], profiles[fleet], cities
            )
            for _ in range(allocation["roundTrips"]):
                ordinal += 1
                if len(market_hubs) == 1:
                    hub = market_hubs[0]
                    spoke = (
                        market["destination"]
                        if market["origin"] == hub
                        else market["origin"]
                    )
                    feasible = []
                    for bank in windows[hub]:
                        if (
                            enforce_gate_capacity
                            and (
                                touch_load[(bank["id"], "arrival")]
                                >= hub_gate_counts[hub]
                                or touch_load[(bank["id"], "departure")]
                                >= hub_gate_counts[hub]
                            )
                        ):
                            continue
                        if (
                            distinct_pairing_waves
                            and (
                                pairing_wave_load[(spoke, hub, bank["id"])]
                                or pairing_wave_load[(hub, spoke, bank["id"])]
                            )
                        ):
                            continue
                        inbound_arrival = bank["arrivalTargetMinute"]
                        inbound_departure = _local_departure(
                            inbound_arrival, block, spoke, hub, cities
                        )
                        outbound_departure = bank["departureTargetMinute"]
                        outbound_arrival = _local_arrival(
                            outbound_departure, block, hub, spoke, cities
                        )
                        if (
                            _curfew_status(
                                spoke, inbound_departure, inbound_arrival, policy
                            )
                            == "pass"
                            and _curfew_status(
                                hub, outbound_departure, outbound_arrival, policy
                            )
                            == "pass"
                        ):
                            load = (
                                touch_load[(bank["id"], "arrival")]
                                + touch_load[(bank["id"], "departure")]
                            )
                            pairing_gap = min(
                                _nearest_cyclic_gap(
                                    inbound_departure,
                                    pairing_departure_minutes[(spoke, hub)],
                                ),
                                _nearest_cyclic_gap(
                                    outbound_departure,
                                    pairing_departure_minutes[(hub, spoke)],
                                ),
                            )
                            feasible.append(
                                (
                                    load,
                                    -pairing_gap if prefer_pairing_spread else 0,
                                    bank["sequence"],
                                    bank,
                                )
                            )
                    if not feasible:
                        unplaced.extend(
                            {
                                "market": [market["origin"], market["destination"]],
                                "fleet": fleet,
                                "roundTripOrdinal": ordinal,
                                "direction": direction,
                                "reason": "No bank permits a curfew-safe spoke departure",
                            }
                            for direction in ("inbound", "outbound")
                        )
                        continue
                    bank = min(feasible)[-1]
                    inbound_arrival = bank["arrivalTargetMinute"]
                    inbound_departure = _local_departure(
                        inbound_arrival, block, spoke, hub, cities
                    )
                    outbound_departure = bank["departureTargetMinute"]
                    outbound_arrival = _local_arrival(
                        outbound_departure, block, hub, spoke, cities
                    )
                    base = f"{market['origin']}-{market['destination']}-{fleet}-{ordinal}"
                    add_leg(
                        identifier=f"{base}-IN", market=market, fleet=fleet,
                        ordinal=ordinal, direction="inbound", origin=spoke,
                        destination=hub, departure=inbound_departure,
                        arrival=inbound_arrival, block=block,
                        touches=[{"hub": hub, "operation": "arrival", "bankId": bank["id"]}],
                    )
                    add_leg(
                        identifier=f"{base}-OUT", market=market, fleet=fleet,
                        ordinal=ordinal, direction="outbound", origin=hub,
                        destination=spoke, departure=outbound_departure,
                        arrival=outbound_arrival, block=block,
                        touches=[{"hub": hub, "operation": "departure", "bankId": bank["id"]}],
                    )
                    continue

                for direction, origin, destination in (
                    ("outbound", market["origin"], market["destination"]),
                    ("inbound", market["destination"], market["origin"]),
                ):
                    candidates = _interhub_candidates(
                        origin, destination, block, windows, cities,
                        int(bank_rules["interHubSearchStepMinutes"]),
                    )
                    candidates = [
                        row for row in candidates
                        if _curfew_status(origin, row[2], row[3], policy) == "pass"
                        and (
                            not enforce_gate_capacity
                            or (
                                touch_load[(row[0]["id"], "departure")]
                                < hub_gate_counts[origin]
                                and touch_load[(row[1]["id"], "arrival")]
                                < hub_gate_counts[destination]
                            )
                        )
                        and (
                            not distinct_pairing_waves
                            or not pairing_wave_load[
                                (origin, destination, row[0]["id"])
                            ]
                        )
                    ]
                    if not candidates:
                        unplaced.append(
                            {
                                "market": [market["origin"], market["destination"]],
                                "fleet": fleet,
                                "roundTripOrdinal": ordinal,
                                "direction": direction,
                                "reason": "No compatible curfew-safe inter-hub bank pair",
                            }
                        )
                        continue
                    origin_bank, destination_bank, departure, arrival = min(
                        candidates,
                        key=lambda row: (
                            touch_load[(row[0]["id"], "departure")]
                            + touch_load[(row[1]["id"], "arrival")],
                            (
                                -_nearest_cyclic_gap(
                                    row[2],
                                    pairing_departure_minutes[
                                        (origin, destination)
                                    ],
                                )
                                if prefer_pairing_spread
                                else 0
                            ),
                            abs(row[0]["departureTargetMinute"] - row[2])
                            + abs(row[1]["arrivalTargetMinute"] - row[3]),
                            row[2], row[0]["sequence"], row[1]["sequence"],
                        ),
                    )
                    base = (
                        f"{market['origin']}-{market['destination']}-{fleet}-"
                        f"{ordinal}-{direction.upper()}"
                    )
                    add_leg(
                        identifier=base, market=market, fleet=fleet,
                        ordinal=ordinal, direction=direction, origin=origin,
                        destination=destination, departure=departure,
                        arrival=arrival, block=block,
                        touches=[
                            {"hub": origin, "operation": "departure", "bankId": origin_bank["id"]},
                            {
                                "hub": destination,
                                "operation": "arrival",
                                "bankId": destination_bank["id"],
                            },
                        ],
                    )

    curfew_violations = [row for row in placements if row["curfewStatus"] == "fail"]
    expected_hub_legs = sum(
        row["plannedLegs"]
        for row in frequency_plan["markets"]
        if row["origin"] in hub_set or row["destination"] in hub_set
    )
    bank_rows = []
    for hub in hubs:
        bank_rows.append(
            {
                "hub": hub,
                "phaseMinute": phase[hub],
                "bankCount": len(windows[hub]),
                "banks": [
                    {
                        **bank,
                        "arrivalCount": touch_load[(bank["id"], "arrival")],
                        "departureCount": touch_load[(bank["id"], "departure")],
                    }
                    for bank in windows[hub]
                ],
            }
        )
    empty_banks = [
        bank["id"]
        for hub in bank_rows
        for bank in hub["banks"]
        if not bank["arrivalCount"] or not bank["departureCount"]
    ]
    over_capacity_bank_touches = [
        {
            "hub": hub["hub"],
            "bankId": bank["id"],
            "arrivalCount": bank["arrivalCount"],
            "departureCount": bank["departureCount"],
            "gateCount": hub_gate_counts[hub["hub"]],
        }
        for hub in bank_rows
        for bank in hub["banks"]
        if enforce_gate_capacity
        and max(bank["arrivalCount"], bank["departureCount"])
        > hub_gate_counts[hub["hub"]]
    ]
    repeated_pairing_waves = [
        {
            "origin": origin,
            "destination": destination,
            "bankId": bank_id,
            "departures": count,
        }
        for (origin, destination, bank_id), count in sorted(
            pairing_wave_load.items()
        )
        if distinct_pairing_waves and count > 1
    ]
    windows_policy = policy["departureWindows"]
    invalid_windows = [
        bank["id"]
        for hub in bank_rows
        for bank in hub["banks"]
        if bank["endMinute"] - bank["startMinute"] != width
        or bank["startMinute"] < windows_policy["earliestMinute"]
        or bank["endMinute"] > windows_policy["hubOrFocusLatestMinute"]
    ]
    turn_gap = (
        int(bank_rules["hubDepartureOffsetMinutes"])
        - int(bank_rules["spokeArrivalOffsetMinutes"])
    )
    interhub_capacity = (
        _interhub_spacing_capacity(
            interhub_services,
            windows,
            cities,
            int(bank_rules["interHubSearchStepMinutes"]),
            int(policy["section26"]["hardFloorMinutes"]),
        )
        if bank_rules.get("requireInterhubSpacingCapacity", False)
        else []
    )
    interhub_capacity_shortfall = sum(
        row["shortfall"] for row in interhub_capacity
    )
    checks = [
        {
            "id": "bank_window_definition",
            "status": "pass" if not invalid_windows else "fail",
            "message": (
                f"Generated all {sum(bank_counts.values())} effective 60-minute bank cores"
                if not invalid_windows
                else "Invalid bank windows: " + ", ".join(invalid_windows)
            ),
        },
        {
            "id": "hub_service_placement",
            "status": "pass" if not unplaced and len(placements) == expected_hub_legs else "fail",
            "message": (
                f"Placed all {expected_hub_legs} proposed hub-touching legs"
                if not unplaced and len(placements) == expected_hub_legs
                else f"{len(unplaced)} proposed hub-touching legs could not be placed"
            ),
        },
        {
            "id": "curfew_enforcement",
            "status": "pass" if not curfew_violations else "fail",
            "hardStop": True,
            "message": (
                "Every banked leg observes its origin departure window"
                if not curfew_violations
                else f"{len(curfew_violations)} banked legs violate a curfew"
            ),
        },
        {
            "id": "connection_turn_floor",
            "status": "pass" if turn_gap >= policy["turns"]["minimumMinutes"] else "fail",
            "message": (
                f"Spoke arrivals precede hub departures by {turn_gap} minutes"
                if turn_gap >= policy["turns"]["minimumMinutes"]
                else (
                    f"The {turn_gap}-minute bank turn is below the "
                    f"{policy['turns']['minimumMinutes']}-minute floor"
                )
            ),
        },
        {
            "id": "bank_directional_use",
            "status": "pass" if not empty_banks else "fail",
            "message": (
                "Every generated bank contains both arrivals and departures"
                if not empty_banks
                else "Banks without both directions: " + ", ".join(empty_banks)
            ),
        },
    ]
    if enforce_gate_capacity:
        checks.append(
            {
                "id": "bank_passenger_touch_capacity",
                "status": "pass" if not over_capacity_bank_touches else "fail",
                "message": (
                    "Every bank keeps arrivals and departures within configured gate capacity"
                    if not over_capacity_bank_touches
                    else f"{len(over_capacity_bank_touches)} bank-direction loads exceed configured gates"
                ),
            }
        )
    if distinct_pairing_waves:
        checks.append(
            {
                "id": "pairing_wave_spacing_capacity",
                "status": "pass" if not repeated_pairing_waves else "fail",
                "message": (
                    "Every directed pairing uses each assigned wave at most once"
                    if not repeated_pairing_waves
                    else f"{len(repeated_pairing_waves)} pairing-wave assignments repeat inside one core"
                ),
            }
        )
    if bank_rules.get("requireInterhubSpacingCapacity", False):
        checks.append(
            {
                "id": "interhub_spacing_capacity",
                "status": "pass" if not interhub_capacity_shortfall else "fail",
                "message": (
                    "Every directed inter-hub frequency fits distinct Section 2.6-compliant exact-grid slots"
                    if not interhub_capacity_shortfall
                    else f"Inter-hub bank overlap is short {interhub_capacity_shortfall} spaced departure slots"
                ),
            }
        )
    failed = sum(check["status"] == "fail" for check in checks)
    return {
        "schemaVersion": "1.0.0",
        "scheduleId": canonical["schedule"]["id"],
        "sourceKind": "frequency_fleet_bank_placement",
        "planningRulesId": planning_rules["id"],
        "operatingPolicyId": policy["id"],
        "status": "pass" if failed == 0 else "fail",
        "summary": {
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
            "hubs": len(hubs),
            "banks": sum(bank_counts.values()),
            "bankCountSource": (
                "planning_rules_override"
                if bank_counts != policy_bank_counts
                else "operating_policy"
            ),
            "hubMarketLegs": expected_hub_legs,
            "placedLegs": len(placements),
            "unplacedLegs": len(unplaced),
            "bankTouchAssignments": sum(len(row["bankTouches"]) for row in placements),
            "nonHubLegsPendingRouting": (
                frequency_plan["summary"]["plannedLegs"] - expected_hub_legs
            ),
            "curfewViolations": len(curfew_violations),
            **(
                {
                    "interHubSpacingCapacityShortfall": interhub_capacity_shortfall
                }
                if bank_rules.get("requireInterhubSpacingCapacity", False)
                else {}
            ),
        },
        "checks": checks,
        "hubs": bank_rows,
        "bankCountPolicy": {
            "source": (
                "planning_rules_override"
                if bank_counts != policy_bank_counts
                else "operating_policy"
            ),
            "operatingPolicyCounts": dict(sorted(policy_bank_counts.items())),
            "effectiveCounts": dict(sorted(bank_counts.items())),
        },
        "placements": placements,
        "unplaced": unplaced,
        "bankTouchCapacityViolations": over_capacity_bank_touches,
        "pairingWaveSpacingViolations": repeated_pairing_waves,
        **(
            {"interHubSpacingCapacity": interhub_capacity}
            if bank_rules.get("requireInterhubSpacingCapacity", False)
            else {}
        ),
        "limitations": [
            "Bank placement assigns local clock times to proposed hub service but "
            "does not yet join those legs into aircraft routes.",
            "Non-hub point-to-point and focus-city flying remains untimed until "
            "the routing stage can place it around banked work.",
            "Gate capacity, RON placement, route continuity, and flight numbering "
            "remain mandatory downstream checks.",
        ],
    }


def build_hub_bank_plan_from_manifest(
    canonical: dict[str, Any],
    frequency_plan: dict[str, Any],
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    loaded = load_demand_sources_from_manifest(manifest_path, repo_root)
    if loaded["manifest"]["id"] != frequency_plan["demandDataVersion"]:
        raise ValueError("Frequency plan version does not match the bank manifest")
    return build_hub_bank_plan(
        canonical, frequency_plan, loaded["planningRules"]
    )
