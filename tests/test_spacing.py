from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.spacing import pairing_spacing_rule


class PairingSpacingRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        policy = json.loads(
            (REPO_ROOT / "config" / "policies" / "operating_rules_v2_0.json").read_text()
        )
        cls.section26 = policy["section26"]
        cls.hubs = {"DAY", "JAX", "MCI", "PHF", "RFD", "SFB", "SYR"}

    def test_non_hub_target_uses_station_factor_and_tolerance(self) -> None:
        rule = pairing_spacing_rule(
            "PHF", "SAV", 4, 4, self.hubs, self.section26
        )
        self.assertEqual(rule["targetMinutes"], 120.0)
        self.assertEqual(rule["minimumGapMinutes"], 108.0)
        self.assertEqual(rule["allowedExceptions"], 1)
        self.assertFalse(rule["hubBound"])

    def test_low_frequency_pairing_has_no_exception(self) -> None:
        rule = pairing_spacing_rule(
            "PHF", "SAV", 3, 4, self.hubs, self.section26
        )
        self.assertEqual(rule["targetMinutes"], 160.0)
        self.assertEqual(rule["minimumGapMinutes"], 144.0)
        self.assertEqual(rule["allowedExceptions"], 0)

    def test_hub_bound_pairing_uses_only_hard_floor(self) -> None:
        rule = pairing_spacing_rule(
            "SAV", "PHF", 6, 20, self.hubs, self.section26
        )
        self.assertEqual(rule["targetMinutes"], 30.0)
        self.assertEqual(rule["minimumGapMinutes"], 30.0)
        self.assertEqual(rule["hardFloorMinutes"], 30)
        self.assertEqual(rule["allowedExceptions"], 0)
        self.assertTrue(rule["hubBound"])

    def test_target_is_capped_before_tolerance(self) -> None:
        rule = pairing_spacing_rule(
            "PHF", "SAV", 1, 1, self.hubs, self.section26
        )
        self.assertEqual(rule["targetMinutes"], 240.0)
        self.assertEqual(rule["minimumGapMinutes"], 216.0)


if __name__ == "__main__":
    unittest.main()
