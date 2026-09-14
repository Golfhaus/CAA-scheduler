from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.demand import (
    build_demand_plan_from_manifest,
    parse_airport_od_matrix,
)


CANONICAL_PATH = (
    REPO_ROOT
    / "data"
    / "schedules"
    / "schedule_6_v2_2_5"
    / "canonical_schedule.json"
)
MATRIX_PATH = REPO_ROOT / "data" / "reference" / "airport_od_matrix_consolidated_v2.csv"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v1.json"


class DemandPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = json.loads(CANONICAL_PATH.read_text())

    def test_matrix_is_complete_directional_numeric_input(self) -> None:
        matrix = parse_airport_od_matrix(MATRIX_PATH.read_text())
        self.assertEqual(len(matrix["airports"]), 105)
        self.assertEqual(len(matrix["values"]), 105)
        self.assertIn("BTR", matrix["airports"])
        self.assertIn("CHS", matrix["airports"])
        self.assertEqual(matrix["marketSizes"]["BTR"], 194.9)
        self.assertEqual(matrix["marketSizes"]["CHS"], 1198.5)
        self.assertEqual(matrix["directionalPassengersPerDay"], 101247.1)

    def test_real_inputs_reproduce_every_hub_assignment(self) -> None:
        expected = {
            city["code"]: city["hubAssignments"]
            for city in self.canonical["cities"]
            if city["role"] != "hub"
        }
        plan = build_demand_plan_from_manifest(
            MANIFEST_PATH,
            REPO_ROOT,
            self.canonical["cities"],
            expected_hub_assignments=expected,
        )
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["summary"], {"checks": 2, "passed": 2, "failed": 0})
        self.assertEqual(plan["matrix"]["airportCount"], 105)
        self.assertEqual(plan["assignmentParity"]["matched"], 100)
        self.assertEqual(plan["assignmentParity"]["differences"], [])
        by_code = {
            city["code"]: city
            for city in plan["multiHubAssignments"]["cities"]
        }
        self.assertEqual(by_code["CHS"]["hubAssignments"], ["JAX", "PHF", "DAY"])
        self.assertEqual(by_code["BTR"]["hubAssignments"], ["JAX"])

    def test_manifest_fingerprint_mismatch_is_rejected(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text())
        manifest["sources"]["airportOdMatrix"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                build_demand_plan_from_manifest(
                    path,
                    REPO_ROOT,
                    self.canonical["cities"],
                )

    def test_incomplete_matrix_is_rejected(self) -> None:
        text = MATRIX_PATH.read_text().replace(",CHS,", ",", 1)
        with self.assertRaises(ValueError):
            parse_airport_od_matrix(text)


if __name__ == "__main__":
    unittest.main()
