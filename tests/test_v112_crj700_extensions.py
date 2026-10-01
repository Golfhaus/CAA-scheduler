from __future__ import annotations

import os
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
from caa_scheduler.planning import (
    reconstruct_planning_snapshot,
    validate_planning_snapshot,
)
from caa_scheduler.validation import validate_schedule


@unittest.skip("Archival schedule regression retired; only the latest release is required")
class V112RouteExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_1"
            / "canonical_schedule.json"
        )
        cls.round_one_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_2_round_1.json"
        )
        cls.round_two_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_2_round_2.json"
        )
        cls.round_one = apply_optimization_overlay(
            cls.base,
            cls.round_one_overlay,
        )
        cls.candidate = apply_optimization_overlay(
            cls.round_one,
            cls.round_two_overlay,
        )
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

    def test_mci_route_extensions_use_all_requested_aircraft_and_markets(self) -> None:
        expected = {
            101: ["TOL", "DAY", "BNA", "DAY", "ATW", "MCI", "MSN", "MCI", "ATW"],
            133: ["SHV", "MCI", "SDF", "MCI"],
            152: ["MCI", "SHV", "MCI", "SBN", "MCI"],
            153: ["MCI", "OMA", "MCI", "SDF", "MCI", "XNA", "BHM", "VPS"],
            526: ["SAT", "MCI", "MSN", "MCI", "ATW", "MCI", "RDU"],
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

        directed = Counter(
            (leg["origin"], leg["destination"])
            for leg in self.candidate["legs"]
        )
        self.assertEqual(directed[("MCI", "MSN")], 2)
        self.assertEqual(directed[("MSN", "MCI")], 2)
        self.assertEqual(directed[("MCI", "ATW")], 2)
        self.assertEqual(directed[("ATW", "MCI")], 2)
        self.assertEqual(directed[("MCI", "SBN")], 1)
        self.assertEqual(directed[("SBN", "MCI")], 1)
        self.assertEqual(directed[("MCI", "SDF")], 2)
        self.assertEqual(directed[("SDF", "MCI")], 2)

    def test_round_two_overlay_is_deterministic(self) -> None:
        self.assertEqual(
            apply_optimization_overlay(self.round_one, self.round_two_overlay),
            apply_optimization_overlay(self.round_one, self.round_two_overlay),
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
        self.assertEqual(aircraft_days(self.candidate)["CRJ200"], 76)
        self.assertEqual(aircraft_days(self.candidate)["CRJ900"], 28)

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
        planning = reconstruct_planning_snapshot(self.candidate)
        self.assertEqual(
            validate_planning_snapshot(planning, self.candidate)["status"],
            "pass",
        )

        stands = [
            claim
            for city in self.gates["cities"]
            for claim in city["claims"]
            if claim["rowType"] == "stand"
        ]
        self.assertEqual(len(self.candidate["legs"]), 970)
        self.assertEqual(len(stands), 32)
        self.assertEqual(
            sum(claim["end"] - claim["start"] for claim in stands),
            19729,
        )
        mci = next(city for city in self.gates["cities"] if city["code"] == "MCI")
        mci_stands = [
            claim for claim in mci["claims"] if claim["rowType"] == "stand"
        ]
        self.assertEqual(len(mci_stands), 8)
        self.assertEqual(
            sum(claim["end"] - claim["start"] for claim in mci_stands),
            4822,
        )

    def test_release_is_exposed_as_the_app_default(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_2_feasibility_01", exposed)
        self.assertNotIn("schedule_7_v1_1_2_feasibility_02", exposed)
        self.assertIn("schedule_7_v1_1_2", exposed)


if __name__ == "__main__":
    unittest.main()
