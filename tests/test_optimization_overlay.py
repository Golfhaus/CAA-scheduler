from __future__ import annotations

import copy
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
        cls.round_two = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_0_round_2.json"
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

    def test_round_two_adds_all_remaining_targets_with_fixed_inventory(self) -> None:
        round_one = apply_optimization_overlay(self.base, self.overlay)
        first = apply_optimization_overlay(round_one, self.round_two)
        second = apply_optimization_overlay(round_one, self.round_two)
        self.assertEqual(first, second)
        self.assertEqual(len(first["legs"]), 948)
        self.assertEqual(len({leg["route"] for leg in first["legs"]}), 179)
        self.assertEqual(len({leg["line"] for leg in first["legs"]}), 22)
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
        unused = next(
            check for check in operating["checks"] if check["id"] == "unused_overrides"
        )
        self.assertEqual(unused["status"], "pass")

        new_legs = [
            leg for leg in first["legs"] if int(leg["route"]) in {352, 353, 354}
        ]
        self.assertEqual(len(new_legs), 16)
        self.assertEqual(
            {
                city
                for leg in new_legs
                for city in (leg["origin"], leg["destination"])
                if city != "PHF"
            },
            {"MHT", "ALB", "ROC", "MLB", "PGD", "SRQ", "VPS", "PNS"},
        )

        gates = export_gate_schedule(first)
        phf = next(city for city in gates["cities"] if city["code"] == "PHF")
        self.assertEqual(phf["peakUsed"], 22)
        self.assertEqual(
            sum(
                claim["rowType"] == "stand"
                for city in gates["cities"]
                for claim in city["claims"]
            ),
            52,
        )

    def test_new_route_overlay_rejects_duplicate_and_discontinuous_routes(self) -> None:
        round_one = apply_optimization_overlay(self.base, self.overlay)
        duplicate = copy.deepcopy(self.round_two)
        duplicate["addRoutes"][0]["route"] = 307
        with self.assertRaisesRegex(ValueError, "route already exists"):
            apply_optimization_overlay(round_one, duplicate)

        discontinuous = copy.deepcopy(self.round_two)
        discontinuous["addRoutes"][0]["legs"][1]["origin"] = "PNS"
        with self.assertRaisesRegex(ValueError, "is discontinuous"):
            apply_optimization_overlay(round_one, discontinuous)


if __name__ == "__main__":
    unittest.main()
