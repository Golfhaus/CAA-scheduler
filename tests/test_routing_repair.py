from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.routing_repair import (
    _euler_circuits,
    build_routing_repair_plan_from_manifest,
)


SCHEDULE_DIRECTORY = REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v3.json"


class RoutingRepairPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = json.loads(
            (SCHEDULE_DIRECTORY / "canonical_schedule.json").read_text()
        )
        cls.frequency_plan = json.loads(
            (SCHEDULE_DIRECTORY / "frequency_fleet_plan.json").read_text()
        )
        cls.bank_plan = json.loads(
            (SCHEDULE_DIRECTORY / "hub_bank_plan.json").read_text()
        )
        cls.plan = cls.build()

    @classmethod
    def build(cls, canonical=None):
        return build_routing_repair_plan_from_manifest(
            canonical or cls.canonical,
            cls.frequency_plan,
            cls.bank_plan,
            MANIFEST_PATH,
            REPO_ROOT,
        )

    def test_repair_fits_every_leg_inside_schedule_selected_fleet(self) -> None:
        summary = self.plan["summary"]
        self.assertEqual(self.plan["status"], "pass")
        self.assertEqual(summary["plannedLegs"], 1430)
        self.assertEqual(summary["routedLegs"], 1430)
        self.assertEqual(summary["configuredAircraft"], 225)
        self.assertEqual(summary["requiredAircraft"], 209)
        self.assertEqual(summary["remainingAircraft"], 16)
        self.assertEqual(summary["aircraftShortfall"], 0)

    def test_repair_preserves_hard_curfews_and_ron_requirements(self) -> None:
        self.assertEqual(self.plan["summary"]["curfewViolations"], 0)
        self.assertEqual(self.plan["summary"]["destinationsWithoutRon"], 0)
        self.assertEqual(self.plan["summary"]["rollingRonViolations"], 0)
        checks = {check["id"]: check for check in self.plan["checks"]}
        self.assertTrue(checks["curfew_enforcement"]["hardStop"])
        self.assertTrue(all(check["status"] == "pass" for check in checks.values()))

    def test_repair_routes_are_continuous_and_cover_each_leg_once(self) -> None:
        identifiers = [leg["id"] for leg in self.plan["legs"]]
        routed = [identifier for route in self.plan["routes"] for identifier in route["legIds"]]
        self.assertEqual(len(identifiers), 1430)
        self.assertEqual(len(set(identifiers)), 1430)
        self.assertCountEqual(routed, identifiers)
        self.assertEqual(self.plan["diagnostics"]["continuityViolations"], [])
        self.assertEqual(self.plan["diagnostics"]["turnViolations"], [])

    def test_fleet_counts_are_read_only_from_the_schedule(self) -> None:
        reduced = copy.deepcopy(self.canonical)
        reduced["schedule"]["fleetCounts"]["CRJ200"] = 60
        plan = self.build(reduced)
        self.assertEqual(plan["fleetPlan"]["CRJ200"]["configuredAircraft"], 60)
        self.assertEqual(plan["status"], "fail")

    def test_bank_alignment_is_an_explicit_materialization_blocker(self) -> None:
        self.assertEqual(self.plan["materializationStatus"], "pending_bank_alignment")
        self.assertEqual(self.plan["materialization"]["status"], "pending")
        self.assertLess(
            self.plan["summary"]["bankAlignedLegs"],
            self.plan["summary"]["bankTouchLegs"],
        )

    def test_disconnected_balanced_inventory_builds_separate_circuits(self) -> None:
        legs = [
            {"id": "A-B", "origin": "A", "destination": "B"},
            {"id": "B-A", "origin": "B", "destination": "A"},
            {"id": "C-D", "origin": "C", "destination": "D"},
            {"id": "D-C", "origin": "D", "destination": "C"},
        ]
        circuits = _euler_circuits(legs, 0)
        self.assertEqual(len(circuits), 2)
        self.assertCountEqual(
            [leg["id"] for circuit in circuits for leg in circuit],
            [leg["id"] for leg in legs],
        )


if __name__ == "__main__":
    unittest.main()
