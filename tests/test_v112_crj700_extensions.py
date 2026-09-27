from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.io import read_json
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule


class V112Crj700ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_1"
            / "canonical_schedule.json"
        )
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_2_round_1.json"
        )
        cls.candidate = apply_optimization_overlay(cls.base, cls.overlay)
        cls.gates = export_gate_schedule(
            cls.candidate,
            rejoin_avoidable_tows=True,
        )

    def test_short_crj700_routes_gain_geographically_coherent_flying(self) -> None:
        expected = {
            306: ["CLT", "BDL", "CLT", "SYR"],
            323: ["SRQ", "SYR", "PHF", "SYR"],
            344: ["SRQ", "SYR", "MCI", "HRL", "MCI"],
            350: ["ELP", "MCI", "ELP", "MCI", "ELP"],
        }
        for route, path in expected.items():
            legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [legs[0]["origin"], *[leg["destination"] for leg in legs]],
                path,
            )

    def test_overlay_retains_every_released_leg_and_aircraft_day(self) -> None:
        base_legs = {leg["id"]: leg for leg in self.base["legs"]}
        candidate_legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        retained_fields = {
            "route",
            "line",
            "fleet",
            "day",
            "pairing",
            "flight",
            "origin",
            "destination",
            "departureMinute",
            "arrivalMinute",
        }
        for identifier, base_leg in base_legs.items():
            self.assertIn(identifier, candidate_legs)
            self.assertEqual(
                {field: base_leg[field] for field in retained_fields},
                {
                    field: candidate_legs[identifier][field]
                    for field in retained_fields
                },
            )

        def aircraft_days(schedule: dict) -> Counter[str]:
            return Counter(
                fleet
                for fleet, _line, _day in {
                    (leg["fleet"], leg["line"], leg["day"])
                    for leg in schedule["legs"]
                }
            )

        self.assertEqual(aircraft_days(self.candidate), aircraft_days(self.base))
        self.assertEqual(aircraft_days(self.candidate)["CRJ700"], 54)

    def test_candidate_passes_hard_validation_and_fixed_inventory(self) -> None:
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(
            any(
                check["hardStop"] and check["status"] == "fail"
                for check in operating["checks"]
            )
        )

        stands = [
            claim
            for city in self.gates["cities"]
            for claim in city["claims"]
            if claim["rowType"] == "stand"
        ]
        self.assertEqual(len(stands), 33)
        self.assertEqual(
            sum(claim["end"] - claim["start"] for claim in stands),
            21037,
        )

    def test_candidate_is_not_exposed_in_the_app_manifest(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        self.assertNotIn(
            "schedule_7_v1_1_2_feasibility_01",
            {schedule["id"] for schedule in manifest["schedules"]},
        )


if __name__ == "__main__":
    unittest.main()
