from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.allocation import build_frequency_fleet_plan_from_manifest


SCHEDULE_DIRECTORY = REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v3.json"
STRICT_MANIFEST_PATH = (
    REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v4.json"
)
SPACING_MANIFEST_PATH = (
    REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v5.json"
)


class FrequencyFleetPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = json.loads(
            (SCHEDULE_DIRECTORY / "canonical_schedule.json").read_text()
        )
        cls.demand_plan = json.loads(
            (SCHEDULE_DIRECTORY / "demand_plan.json").read_text()
        )

    def build(self, canonical=None):
        return build_frequency_fleet_plan_from_manifest(
            canonical or self.canonical,
            self.demand_plan,
            MANIFEST_PATH,
            REPO_ROOT,
        )

    def test_complete_demand_allocation_passes_all_planning_checks(self) -> None:
        plan = self.build()
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["summary"]["candidateMarkets"], 368)
        self.assertEqual(plan["summary"]["newRequiredHubMarkets"], 34)
        self.assertEqual(plan["summary"]["mandatoryRoundTrips"], 526)
        self.assertEqual(plan["summary"]["optionalRoundTrips"], 189)
        self.assertEqual(plan["summary"]["plannedLegs"], 1430)
        self.assertEqual(plan["summary"]["pointToPointLegs"], 126)
        self.assertLessEqual(plan["summary"]["pointToPointShare"], 0.1)
        self.assertTrue(all(check["status"] == "pass" for check in plan["checks"]))

    def test_newly_required_hub_markets_are_added(self) -> None:
        plan = self.build()
        by_market = {
            (row["origin"], row["destination"]): row for row in plan["markets"]
        }
        chs_phf = by_market[("CHS", "PHF")]
        chs_day = by_market[("CHS", "DAY")]
        self.assertFalse(chs_phf["existingMarket"])
        self.assertTrue(chs_phf["requiredByHubPlan"])
        self.assertGreaterEqual(chs_phf["plannedRoundTrips"], 1)
        self.assertFalse(chs_day["existingMarket"])
        self.assertTrue(chs_day["requiredByHubPlan"])

    def test_strict_tier_boundary_removes_stale_service_markets(self) -> None:
        demand = copy.deepcopy(self.demand_plan)
        demand["demandDataVersion"] = "bts-db1c-6mo-jul2025-apr2026-v4"
        plan = build_frequency_fleet_plan_from_manifest(
            self.canonical,
            demand,
            STRICT_MANIFEST_PATH,
            REPO_ROOT,
        )
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["summary"]["candidateMarkets"], 235)
        self.assertEqual(plan["summary"]["plannedLegs"], 1430)
        self.assertEqual(plan["summary"]["removedHistoricalServiceMarkets"], 131)
        self.assertEqual(plan["summary"]["focusCitySubstitutions"], 20)
        service = {row["code"]: row for row in plan["cityService"]}
        self.assertEqual(
            service["AUS"]["serviceAssignments"],
            ["MCI", "JAX", "DAY", "BHM"],
        )
        self.assertEqual(service["FWA"]["serviceAssignments"], ["DAY"])
        removed = {
            (row["origin"], row["destination"])
            for row in plan["networkReconciliation"][
                "removedHistoricalServiceMarkets"
            ]
        }
        self.assertIn(("BHM", "FWA"), removed)
        self.assertIn(("ABE", "JAX"), removed)

    def test_spacing_policy_reserves_routing_capacity_and_one_fleet_per_market(self) -> None:
        demand = copy.deepcopy(self.demand_plan)
        demand["demandDataVersion"] = "bts-db1c-6mo-jul2025-apr2026-v5"
        plan = build_frequency_fleet_plan_from_manifest(
            self.canonical,
            demand,
            SPACING_MANIFEST_PATH,
            REPO_ROOT,
        )
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["summary"]["plannedLegs"], 1406)
        self.assertEqual(plan["summary"]["maximumPlannedLegs"], 1430)
        self.assertEqual(plan["summary"]["routingReserveRoundTrips"], 12)
        self.assertEqual(plan["summary"]["mixedFleetMarkets"], 0)
        self.assertTrue(
            all(len(market["allocations"]) == 1 for market in plan["markets"])
        )

    def test_fleet_counts_come_from_the_schedule(self) -> None:
        changed = copy.deepcopy(self.canonical)
        changed["schedule"]["fleetCounts"]["MAX9"] = 34
        plan = self.build(changed)
        self.assertEqual(plan["fleetPlan"]["MAX9"]["aircraftCount"], 34)
        self.assertEqual(plan["fleetPlan"]["MAX9"]["availableAircraftMinutes"], 30600)
        self.assertLess(plan["summary"]["plannedLegs"], 1430)

    def test_insufficient_schedule_fleet_is_reported_not_overallocated(self) -> None:
        changed = copy.deepcopy(self.canonical)
        changed["schedule"]["fleetCounts"] = {
            "MAX9": 1,
            "CRJ900": 0,
            "CRJ700": 0,
            "CRJ200": 0,
        }
        plan = self.build(changed)
        self.assertEqual(plan["status"], "fail")
        self.assertGreater(plan["summary"]["unassignedMandatoryRoundTrips"], 0)
        self.assertEqual(plan["summary"]["optionalRoundTrips"], 0)
        checks = {check["id"]: check for check in plan["checks"]}
        self.assertEqual(checks["mandatory_capacity"]["status"], "fail")
        self.assertLessEqual(
            plan["fleetPlan"]["MAX9"]["plannedAircraftMinutes"],
            plan["fleetPlan"]["MAX9"]["availableAircraftMinutes"],
        )

    def test_allocation_is_deterministic(self) -> None:
        self.assertEqual(self.build(), self.build())

    def test_new_fleet_type_requires_a_versioned_performance_profile(self) -> None:
        changed = copy.deepcopy(self.canonical)
        changed["schedule"]["fleetCounts"]["UNKNOWN"] = 1
        with self.assertRaisesRegex(ValueError, "no performance profile"):
            self.build(changed)


if __name__ == "__main__":
    unittest.main()
