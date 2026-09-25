from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.io import read_json
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule


class OptimizationOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_0_0"
            / "canonical_schedule.json"
        )
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_0_round_1.json"
        )

    def test_round_one_overlay_is_deterministic_and_fully_feasible(self) -> None:
        first = apply_optimization_overlay(self.base, self.overlay)
        second = apply_optimization_overlay(self.base, self.overlay)
        self.assertEqual(first, second)
        self.assertEqual(len(first["legs"]), 932)
        self.assertEqual(validate_schedule(first)["status"], "pass")

        operating = validate_operating_rules(first)
        self.assertNotEqual(operating["status"], "fail")
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(
            any(
                check["hardStop"] and check["status"] == "fail"
                for check in operating["checks"]
            )
        )

        gates = export_gate_schedule(first)
        phf = next(city for city in gates["cities"] if city["code"] == "PHF")
        self.assertEqual(phf["peakUsed"], 21)
        self.assertEqual(
            sum(
                claim["rowType"] == "stand"
                for city in gates["cities"]
                for claim in city["claims"]
            ),
            45,
        )

    def test_overlay_rejects_a_stale_retime_anchor(self) -> None:
        stale = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_0_0"
            / "canonical_schedule.json"
        )
        leg = next(
            item
            for item in stale["legs"]
            if item["id"] == "CLT-PHF-CRJ700-04-OUT"
        )
        leg["departureMinute"] += 5
        with self.assertRaisesRegex(ValueError, "Stale overlay"):
            apply_optimization_overlay(stale, self.overlay)


if __name__ == "__main__":
    unittest.main()
