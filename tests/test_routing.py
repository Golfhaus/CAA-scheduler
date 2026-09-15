from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.routing import build_aircraft_route_plan_from_manifest


SCHEDULE_DIRECTORY = REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
MANIFEST_PATH = REPO_ROOT / "config" / "demand_data" / "bts_db1c_6mo_v3.json"


class AircraftRoutePlanTests(unittest.TestCase):
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
        cls.plan = cls.build()

    @classmethod
    def build(cls, canonical=None):
        return build_aircraft_route_plan_from_manifest(
            canonical or cls.canonical,
            cls.frequency_plan,
            cls.bank_plan,
            MANIFEST_PATH,
            REPO_ROOT,
        )

    def test_routes_every_proposed_leg_without_curfew_violation(self) -> None:
        summary = self.plan["summary"]
        self.assertEqual(summary["plannedLegs"], 1430)
        self.assertEqual(summary["routedLegs"], 1430)
        self.assertEqual(summary["bankedLegs"], 1190)
        self.assertEqual(summary["insertedNonHubLegs"], 240)
        self.assertEqual(summary["unplacedRoundTrips"], 0)
        self.assertEqual(summary["curfewViolations"], 0)
        self.assertEqual(len(self.plan["unplaced"]), 0)

    def test_cycles_are_continuous_and_cover_each_leg_once(self) -> None:
        identifiers = [
            identifier
            for cycle in self.plan["cycles"]
            for identifier in cycle["legIds"]
        ]
        self.assertEqual(len(identifiers), 1430)
        self.assertEqual(len(set(identifiers)), 1430)
        self.assertEqual(
            {check["id"]: check["status"] for check in self.plan["checks"]},
            {
                "service_coverage": "pass",
                "routing_continuity": "pass",
                "minimum_turns": "pass",
                "fleet_capacity": "fail",
                "curfew_enforcement": "pass",
                "destination_ron_coverage": "pass",
                "rolling_target_ron": "fail",
            },
        )
        curfew_check = next(
            check
            for check in self.plan["checks"]
            if check["id"] == "curfew_enforcement"
        )
        self.assertTrue(curfew_check["hardStop"])

    def test_current_bank_timing_exposes_fleet_shortfall(self) -> None:
        self.assertEqual(self.plan["summary"]["configuredAircraft"], 225)
        self.assertEqual(self.plan["summary"]["requiredAircraft"], 409)
        self.assertEqual(self.plan["summary"]["aircraftShortfall"], 184)
        self.assertEqual(
            {
                fleet: row["shortfall"]
                for fleet, row in self.plan["fleetPlan"].items()
            },
            {"MAX9": 10, "CRJ900": 37, "CRJ700": 49, "CRJ200": 88},
        )

    def test_fleet_capacity_comes_only_from_the_schedule(self) -> None:
        changed = copy.deepcopy(self.canonical)
        changed["schedule"]["fleetCounts"] = {
            fleet: row["requiredAircraft"]
            for fleet, row in self.plan["fleetPlan"].items()
        }
        rerun = self.build(changed)
        self.assertEqual(rerun["summary"]["aircraftShortfall"], 0)
        self.assertTrue(
            all(row["shortfall"] == 0 for row in rerun["fleetPlan"].values())
        )
        fleet_check = next(
            check for check in rerun["checks"] if check["id"] == "fleet_capacity"
        )
        self.assertEqual(fleet_check["status"], "pass")

    def test_ron_diagnostics_are_explicit_and_deterministic(self) -> None:
        self.assertEqual(self.plan["summary"]["destinationsWithoutRon"], 0)
        self.assertEqual(self.plan["summary"]["rollingRonViolations"], 1)
        self.assertEqual(self.plan, self.build())


if __name__ == "__main__":
    unittest.main()
