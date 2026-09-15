from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.bank_materialization import (
    build_bank_materialization_diagnostic_from_manifest,
)


SCHEDULE_DIRECTORY = REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v3.json"


class BankMaterializationDiagnosticTests(unittest.TestCase):
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
        cls.diagnostic = build_bank_materialization_diagnostic_from_manifest(
            cls.canonical,
            cls.frequency_plan,
            cls.bank_plan,
            MANIFEST_PATH,
            REPO_ROOT,
        )

    def test_directions_are_independently_bank_assigned(self) -> None:
        self.assertEqual(
            self.diagnostic["directionalBankAssignment"], "independent"
        )
        self.assertEqual(
            self.diagnostic["bankWindowTiming"],
            "full_core_five_minute_options",
        )
        check = next(
            row
            for row in self.diagnostic["checks"]
            if row["id"] == "directional_bank_assignment"
        )
        self.assertEqual(check["status"], "pass")

    def test_full_bank_window_lower_bound_fits_each_selected_fleet(self) -> None:
        self.assertEqual(
            self.diagnostic["status"], "pending_nonhub_integration"
        )
        self.assertEqual(self.diagnostic["summary"]["configuredAircraft"], 225)
        self.assertEqual(
            self.diagnostic["summary"]["bankAndRonMinimumAircraft"], 169
        )
        self.assertEqual(
            self.diagnostic["summary"]["fleetAllocationShortfall"], 0
        )
        crj200 = self.diagnostic["fleetPlan"]["CRJ200"]
        self.assertEqual(crj200["configuredAircraft"], 80)
        self.assertEqual(crj200["bankOnlyMinimumAircraft"], 67)
        self.assertEqual(crj200["bankAndRonMinimumAircraft"], 67)
        self.assertEqual(crj200["shortfall"], 0)

    def test_lower_bound_keeps_curfews_and_destination_rons_hard(self) -> None:
        self.assertEqual(self.diagnostic["summary"]["curfewViolations"], 0)
        self.assertEqual(
            self.diagnostic["summary"]["requiredDestinationRons"], 99
        )
        checks = {row["id"]: row for row in self.diagnostic["checks"]}
        self.assertTrue(checks["curfew_enforcement"]["hardStop"])
        self.assertEqual(checks["destination_ron_lower_bound"]["status"], "pass")

    def test_nonhub_work_and_canonical_identifiers_remain_guarded(self) -> None:
        self.assertEqual(self.diagnostic["summary"]["bankedLegs"], 1190)
        self.assertEqual(self.diagnostic["summary"]["nonHubLegs"], 240)
        self.assertEqual(
            self.diagnostic["nextRepair"]["action"],
            "integrate_nonhub_legs",
        )
        self.assertEqual(self.diagnostic["materializationStatus"], "pending")


if __name__ == "__main__":
    unittest.main()
