from __future__ import annotations

import copy
import json
import random
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.bank_placement import (
    _maximum_spaced_departures,
    build_hub_bank_plan_from_manifest,
)
from caa_scheduler.allocation import build_frequency_fleet_plan_from_manifest
from caa_scheduler.gate_export import _capacity


SCHEDULE_DIRECTORY = REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v3.json"
GATE_CAPACITY_MANIFEST_PATH = (
    REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v6.json"
)


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

    def test_spaced_departure_capacity_matches_exhaustive_cyclic_greedy(self) -> None:
        def exhaustive(departures: set[int], minimum_gap: int) -> int:
            best = 0
            for first in sorted(departures):
                offsets = sorted(
                    (minute - first) % 1440 for minute in departures
                )
                selected: list[int] = []
                for offset in offsets:
                    if not selected or offset - selected[-1] >= minimum_gap:
                        selected.append(offset)
                while (
                    len(selected) > 1
                    and 1440 - selected[-1] + selected[0] < minimum_gap
                ):
                    selected.pop()
                best = max(best, len(selected))
            return best

        randomizer = random.Random(711)
        for _ in range(100):
            departures = set(randomizer.sample(range(0, 1440, 5), 40))
            minimum_gap = randomizer.choice([60, 90, 120, 180])
            self.assertEqual(
                _maximum_spaced_departures(departures, minimum_gap),
                exhaustive(departures, minimum_gap),
            )

    def test_manifest_version_must_match_frequency_plan(self) -> None:
        changed = copy.deepcopy(self.frequency_plan)
        changed["demandDataVersion"] = "another-version"
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_hub_bank_plan_from_manifest(
                self.canonical, changed, MANIFEST_PATH, REPO_ROOT
            )

    def test_capacity_override_adds_nonoverlapping_bank_waves(self) -> None:
        demand = json.loads(
            (SCHEDULE_DIRECTORY / "demand_plan.json").read_text()
        )
        demand["demandDataVersion"] = "bts-db1c-6mo-jul2025-apr2026-v6"
        frequency = build_frequency_fleet_plan_from_manifest(
            self.canonical,
            demand,
            GATE_CAPACITY_MANIFEST_PATH,
            REPO_ROOT,
        )
        plan = build_hub_bank_plan_from_manifest(
            self.canonical,
            frequency,
            GATE_CAPACITY_MANIFEST_PATH,
            REPO_ROOT,
        )
        self.assertEqual(plan["status"], "pass")
        self.assertEqual(plan["summary"]["banks"], 45)
        self.assertEqual(plan["summary"]["bankCountSource"], "planning_rules_override")
        self.assertEqual(plan["pairingWaveSpacingViolations"], [])
        self.assertEqual(
            plan["bankCountPolicy"]["effectiveCounts"],
            {"DAY": 8, "JAX": 14, "MCI": 10, "PHF": 7, "SYR": 6},
        )
        for hub in plan["hubs"]:
            city = next(
                row for row in self.canonical["cities"] if row["code"] == hub["hub"]
            )
            gate_count = _capacity(city)[0]
            windows = hub["banks"]
            self.assertTrue(
                all(
                    first["endMinute"] <= second["startMinute"]
                    for first, second in zip(windows, windows[1:])
                )
            )
            self.assertTrue(
                all(
                    max(bank["arrivalCount"], bank["departureCount"])
                    <= gate_count
                    for bank in windows
                )
            )


if __name__ == "__main__":
    unittest.main()
