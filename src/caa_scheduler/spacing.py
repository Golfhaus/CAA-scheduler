from __future__ import annotations

import math
from typing import Any


def pairing_spacing_rule(
    origin: str,
    destination: str,
    pairing_departures: int,
    station_departures: int,
    hubs: set[str],
    section26: dict[str, Any],
) -> dict[str, Any]:
    """Return the authoritative Section 2.6 Check A rule for one direction."""
    hard_floor = int(section26["hardFloorMinutes"])
    hub_bound = destination in hubs
    if hub_bound:
        target = float(hard_floor)
        tolerance = float(hard_floor)
        allowed = 0
    else:
        station_factor = math.sqrt(
            float(section26["stationReferenceDepartures"])
            / station_departures
        )
        station_factor = min(
            max(station_factor, float(section26["stationFactorMinimum"])),
            float(section26["stationFactorMaximum"]),
        )
        target = min(
            max(
                float(section26["numeratorMinutes"])
                / pairing_departures
                * station_factor,
                hard_floor,
            ),
            float(section26["pairingTargetMaximumMinutes"]),
        )
        tolerance = target * float(section26["nearTargetTolerance"])
        allowed = (
            1
            if pairing_departures
            >= int(section26["oneExceptionMinimumFrequency"])
            else 0
        )
    return {
        "origin": origin,
        "destination": destination,
        "pairingDepartures": pairing_departures,
        "stationDepartures": station_departures,
        "targetMinutes": target,
        "minimumGapMinutes": max(float(hard_floor), tolerance),
        "hardFloorMinutes": hard_floor,
        "allowedExceptions": allowed,
        "hubBound": hub_bound,
    }
