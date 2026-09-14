from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.planning import (
    compute_multihub_assignments,
    reconstruct_planning_snapshot,
    tier_hub_cap,
    validate_planning_snapshot,
)


class PlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = json.loads(
            (
                REPO_ROOT
                / "data"
                / "schedules"
                / "schedule_6_v2_2_5"
                / "canonical_schedule.json"
            ).read_text()
        )
        cls.rules = json.loads(
            (REPO_ROOT / "config" / "policies" / "planning_rules_v1.json").read_text()
        )
        cls.intergroup_demand = json.loads(
            (REPO_ROOT / "data" / "reference" / "intergroup_demand_v2.json").read_text()
        )

    def test_reconstruction_replaces_pickle_and_stale_station_totals(self) -> None:
        snapshot = reconstruct_planning_snapshot(
            self.canonical, demand_data_version="migration-baseline-unavailable"
        )
        self.assertEqual(snapshot["summary"]["legCount"], 1383)
        self.assertEqual(snapshot["summary"]["marketRows"], 928)
        self.assertEqual(snapshot["summary"]["stationCount"], 105)
        self.assertEqual(sum(snapshot["stationTotals"].values()), 1383)
        self.assertEqual(snapshot["stationTotals"]["BHM"], 46)
        self.assertEqual(snapshot["stationTotals"]["JAX"], 222)
        self.assertEqual(snapshot["fleetPlan"]["MAX9"]["aircraftCount"], 35)
        self.assertEqual(snapshot["fleetPlan"]["MAX9"]["legCount"], 172)
        self.assertEqual(snapshot["fleetPlan"]["MAX9"]["minimumTurnMinutes"], 5480)
        self.assertEqual(snapshot["fleetPlan"]["MAX9"]["requiredAircraftMinutes"], 24327.7)

    def test_reconstructed_snapshot_validates_against_canonical(self) -> None:
        snapshot = reconstruct_planning_snapshot(self.canonical)
        report = validate_planning_snapshot(snapshot, self.canonical)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"], {"checks": 4, "passed": 4, "failed": 0})

    def test_tier_caps_are_data_driven(self) -> None:
        tiers = self.rules["multiHubQualification"]["cityPercentileHubCaps"]
        self.assertEqual(tier_hub_cap(25, tiers), 1)
        self.assertEqual(tier_hub_cap(70, tiers), 2)
        self.assertEqual(tier_hub_cap(89, tiers), 3)
        self.assertEqual(tier_hub_cap(100, tiers), 4)

    def test_multihub_qualification_is_pure_and_deterministic(self) -> None:
        cities = [
            {"code": "H01", "role": "hub", "group": "HUB", "latitude": 0.0, "longitude": 0.0},
            {"code": "H02", "role": "hub", "group": "HUB", "latitude": 0.0, "longitude": 5.0},
            {"code": "H03", "role": "hub", "group": "HUB", "latitude": 0.0, "longitude": 10.0},
            {"code": "AAA", "role": "destination", "group": "G1", "latitude": 0.0, "longitude": 1.0},
            {"code": "AAB", "role": "destination", "group": "G1", "latitude": 0.0, "longitude": 2.0},
            {"code": "BBB", "role": "destination", "group": "G2", "latitude": 0.0, "longitude": 4.0},
            {"code": "CCC", "role": "destination", "group": "G3", "latitude": 0.0, "longitude": 8.0},
        ]
        demand = [
            {"groups": ["G1", "G2"], "qualifiedHubs": ["H01", "H02"], "passengersPerDay": 1000},
            {"groups": ["G1", "G3"], "qualifiedHubs": ["H01", "H02", "H03"], "passengersPerDay": 2000},
            {"groups": ["G2", "G3"], "qualifiedHubs": ["H02", "H03"], "passengersPerDay": 1500},
        ]
        rules = {
            "multiHubQualification": {
                "rankThresholds": [
                    {"rank": "secondary", "minimumServablePassengersPerDay": 400, "maximumDistanceRatio": 6.0},
                    {"rank": "tertiary", "minimumServablePassengersPerDay": 1000, "maximumDistanceRatio": 10.0},
                ],
                "cityPercentileHubCaps": [
                    {"maximumPercentile": 50, "maximumHubs": 1},
                    {"maximumPercentile": 100, "maximumHubs": 3},
                ],
            }
        }
        first = compute_multihub_assignments(
            cities, demand, {"AAA": 10, "AAB": 40, "BBB": 20, "CCC": 30}, rules
        )
        second = compute_multihub_assignments(
            cities, demand, {"AAA": 10, "AAB": 40, "BBB": 20, "CCC": 30}, rules
        )
        self.assertEqual(first, second)
        by_code = {row["code"]: row for row in first["cities"]}
        self.assertEqual(len(by_code["AAA"]["hubAssignments"]), 1)
        self.assertGreaterEqual(len(by_code["AAB"]["hubAssignments"]), 2)

    def test_normalized_intergroup_demand_is_complete_and_external(self) -> None:
        records = self.intergroup_demand["records"]
        groups = {
            city["group"]
            for city in self.canonical["cities"]
            if city["role"] != "hub"
        }
        pairs = {frozenset(row["groups"]) for row in records}
        self.assertEqual(len(groups), 11)
        self.assertEqual(len(records), 55)
        self.assertEqual(len(pairs), 55)
        self.assertTrue(all(set(row["qualifiedHubs"]) <= {"PHF", "SYR", "DAY", "MCI", "JAX"} for row in records))


if __name__ == "__main__":
    unittest.main()
