from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.bank_placement import build_hub_bank_plan_from_manifest


SCHEDULE_DIRECTORY = REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v3.json"


class HubBankPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = json.loads(
            (SCHEDULE_DIRECTORY / "canonical_schedule.json").read_text()
        )
        cls.frequency_plan = json.loads(
            (SCHEDULE_DIRECTORY / "frequency_fleet_plan.json").read_text()
        )
        cls.frequency_plan["demandDataVersion"] = (
            "bts-db1c-6mo-jul2025-apr2026-v3"
        )
        cls.frequency_plan["planningRulesId"] = "caa-planning-rules-v3"

    def build(self, canonical=None):
        return build_hub_bank_plan_from_manifest(
            canonical or self.canonical,
            self.frequency_plan,
            MANIFEST_PATH,
            REPO_ROOT,
        )

    def test_places_every_hub_leg_without_curfew_violation(self) -> None:
        plan = self.build()
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["summary"]["hubs"], 5)
        self.assertEqual(plan["summary"]["banks"], 24)
        self.assertEqual(plan["summary"]["hubMarketLegs"], 1190)
        self.assertEqual(plan["summary"]["placedLegs"], 1190)
        self.assertEqual(plan["summary"]["unplacedLegs"], 0)
        self.assertEqual(plan["summary"]["curfewViolations"], 0)
        self.assertEqual(plan["summary"]["nonHubLegsPendingRouting"], 240)
        self.assertTrue(all(row["curfewStatus"] == "pass" for row in plan["placements"]))

    def test_bank_counts_and_widths_follow_operating_policy(self) -> None:
        plan = self.build()
        expected = self.canonical["operatingPolicy"]["hubBankCounts"]
        for hub in plan["hubs"]:
            self.assertEqual(hub["bankCount"], expected[hub["hub"]])
            for bank in hub["banks"]:
                self.assertEqual(bank["endMinute"] - bank["startMinute"], 60)
                self.assertGreater(bank["arrivalCount"], 0)
                self.assertGreater(bank["departureCount"], 0)

    def test_spoke_bank_targets_preserve_the_turn_floor(self) -> None:
        plan = self.build()
        for hub in plan["hubs"]:
            for bank in hub["banks"]:
                self.assertEqual(
                    bank["departureTargetMinute"] - bank["arrivalTargetMinute"],
                    self.canonical["operatingPolicy"]["turns"]["minimumMinutes"],
                )

    def test_phase_search_is_deterministic(self) -> None:
        self.assertEqual(self.build(), self.build())

    def test_manifest_version_must_match_frequency_plan(self) -> None:
        changed = copy.deepcopy(self.frequency_plan)
        changed["demandDataVersion"] = "another-version"
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_hub_bank_plan_from_manifest(
                self.canonical, changed, MANIFEST_PATH, REPO_ROOT
            )


if __name__ == "__main__":
    unittest.main()
