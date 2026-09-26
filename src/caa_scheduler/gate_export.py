from __future__ import annotations

from typing import Any

from .gates import (
    apply_forced_stand_splits,
    assign_gates,
    build_claims,
    peak_demand,
    serialize_assignments,
)


FLEET_COLORS = {
    "MAX9": "#e3b3a3",
    "CRJ900": "#aec4dc",
    "CRJ700": "#a9cdb2",
    "CRJ200": "#e8cd93",
}

DEFAULT_CAPACITY = {
    "hub": (16, 8),
    "focus_city": (6, 4),
    "destination": (2, 2),
    "unknown": (2, 2),
}


def _capacity(city: dict[str, Any]) -> tuple[int, int]:
    default_gates, default_stands = DEFAULT_CAPACITY[city["role"]]
    return (
        city["gateAllocationOverride"]
        if city["gateAllocationOverride"] is not None
        else default_gates,
        city["standAllocationOverride"]
        if city["standAllocationOverride"] is not None
        else default_stands,
    )


def export_gate_schedule(
    canonical: dict[str, Any],
    *,
    allow_infeasible_preview: bool = False,
    rejoin_avoidable_tows: bool = True,
) -> dict[str, Any]:
    gate_plan = canonical["gatePlan"]
    forced = {
        code: set(labels)
        for code, labels in gate_plan.get("forcedStandSplits", {}).items()
    }
    cities = []
    enforce_fixed_inventory = bool(gate_plan.get("fixedPhysicalInventory", False))
    for city in sorted(canonical["cities"], key=lambda item: item["sourceOrder"]):
        if not city["active"]:
            continue
        gates, stands = _capacity(city)
        claims = build_claims(
            canonical["legs"],
            city["code"],
            cyclic_successor_holds=enforce_fixed_inventory,
        )
        if city["code"] in forced:
            claims = apply_forced_stand_splits(claims, forced[city["code"]])
        stand_middles = None
        if enforce_fixed_inventory:
            assignments, stand_middles = assign_gates(
                claims,
                n_gates=gates,
                n_stands=stands,
                return_provenance=True,
                allow_infeasible_preview=allow_infeasible_preview,
                rejoin_avoidable_tows=rejoin_avoidable_tows,
            )
        else:
            assignments = assign_gates(
                claims,
                n_gates=gates,
                n_stands=None,
            )
        cities.append(
            {
                "code": city["code"],
                "name": city["displayName"],
                "isHub": city["role"] == "hub",
                "isFocusCity": city["role"] == "focus_city",
                "nGates": gates,
                "nStands": stands,
                "peakUsed": peak_demand(claims),
                "claims": serialize_assignments(
                    assignments,
                    gates,
                    n_stands=stands if enforce_fixed_inventory else None,
                    stand_middles=stand_middles,
                ),
            }
        )
    return {
        "label": gate_plan["label"],
        "fleetColors": FLEET_COLORS,
        "cities": cities,
    }
