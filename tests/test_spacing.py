from __future__ import annotations

import json
import sys
import unittest
from collections import defaultdict
from types import SimpleNamespace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from caa_scheduler.spacing import pairing_spacing_rule
from analyze_schedule_7_v1_2_1_holds import HoldSearch


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

    def extension_search(self):
        search = HoldSearch.__new__(HoldSearch)
        search.base = {"legs": [], "operatingPolicy": {"section26": self.section26}}
        search.screen = SimpleNamespace(hubs={"JAX"})
        search.pairs = defaultdict(list)
        return search

    def test_first_daily_round_trip_in_unserved_market_is_spacing_valid(self) -> None:
        search = self.extension_search()
        self.assertTrue(search.spacing([
            {"origin": "HRL", "destination": "JAX", "departureMinute": 1222},
            {"origin": "JAX", "destination": "HRL", "departureMinute": 440},
        ]))

    def test_duplicate_departures_still_fail_extension_screen(self) -> None:
        search = self.extension_search()
        self.assertFalse(search.spacing([
            {"origin": "HRL", "destination": "JAX", "departureMinute": 1222},
            {"origin": "HRL", "destination": "JAX", "departureMinute": 1222},
        ]))

    def test_second_low_frequency_departure_cannot_cluster_at_originator(self) -> None:
        search = self.extension_search()
        search.base["legs"] = [{"origin": "JAX", "destination": "RDU", "departureMinute": 390}]
        search.pairs["JAX", "RDU"] = [390]
        self.assertFalse(search.spacing([
            {"origin": "JAX", "destination": "RDU", "departureMinute": 355},
        ]))

    def test_extension_bank_lookup_normalizes_after_midnight_arrivals(self) -> None:
        search = self.extension_search()
        search.base["hubBanks"] = [{"id": "JAX-T1", "hub": "JAX", "startMinute": 120, "endMinute": 180}]
        self.assertEqual(search.bank("JAX", 1590), "JAX-T1")
        self.assertIsNone(search.bank("JAX", 1620))


if __name__ == "__main__":
    unittest.main()
