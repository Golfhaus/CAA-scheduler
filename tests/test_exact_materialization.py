from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.exact_materialization import blocked_exact_materialization_plan


PLAN_PATH = (
    REPO_ROOT
    / "data"
    / "schedules"
    / "schedule_6_v2_2_5"
    / "exact_materialization_plan.json"
)


class ExactMaterializationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads(PLAN_PATH.read_text())

    def test_every_proposed_leg_has_an_exact_time(self) -> None:
        self.assertEqual(self.plan["status"], "pass")
        self.assertEqual(self.plan["materializationStatus"], "complete")
        self.assertEqual(self.plan["summary"]["plannedLegs"], 1430)
        self.assertEqual(self.plan["summary"]["routedLegs"], 1430)
        self.assertEqual(len(self.plan["legs"]), 1430)

    def test_banked_and_nonhub_flying_are_both_complete(self) -> None:
        self.assertEqual(self.plan["summary"]["bankTouchLegs"], 1190)
        self.assertEqual(self.plan["summary"]["bankAlignedLegs"], 1190)
        self.assertEqual(self.plan["summary"]["nonHubLegs"], 240)
        self.assertEqual(self.plan["summary"]["nonHubIntegratedLegs"], 240)

    def test_selected_fleet_and_hard_curfews_remain_intact(self) -> None:
        self.assertEqual(self.plan["summary"]["configuredAircraft"], 225)
        self.assertEqual(self.plan["summary"]["requiredAircraft"], 208)
        self.assertEqual(self.plan["summary"]["remainingAircraft"], 17)
        self.assertEqual(self.plan["summary"]["curfewViolations"], 0)
        self.assertEqual(self.plan["fleetPlan"]["CRJ200"]["requiredAircraft"], 78)
        self.assertEqual(self.plan["fleetPlan"]["CRJ200"]["configuredAircraft"], 80)

    def test_ron_requirements_are_verified_on_real_cycles(self) -> None:
        self.assertEqual(len(self.plan["ronAssignments"]), 99)
        self.assertEqual(self.plan["summary"]["destinationsWithoutRon"], 0)
        self.assertEqual(self.plan["summary"]["rollingRonViolations"], 0)
        self.assertEqual(self.plan["summary"]["successorSwaps"], 1)
        self.assertEqual(self.plan["nextStep"]["action"], "assign_canonical_identifiers")

    def test_bounded_solver_failure_is_a_durable_blocker(self) -> None:
        blocked = blocked_exact_materialization_plan(
            {
                "schedule": {
                    "id": "schedule_7_test",
                    "fleetCounts": {"CRJ200": 80},
                },
                "operatingPolicy": {"id": "test-policy"},
            },
            {"summary": {"plannedLegs": 1430}},
            "test-rules",
            "Exact CRJ200 materialization failed: time limit reached",
        )
        self.assertEqual(blocked["status"], "fail")
        self.assertEqual(blocked["materializationStatus"], "blocked")
        self.assertEqual(blocked["summary"]["plannedLegs"], 1430)
        self.assertEqual(
            blocked["nextStep"]["action"], "retry_exact_materialization"
        )
        self.assertIn("time limit", blocked["diagnostics"]["solverFailure"])


if __name__ == "__main__":
    unittest.main()
