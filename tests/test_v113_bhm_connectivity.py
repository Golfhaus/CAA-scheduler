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
from caa_scheduler.planning import (
    reconstruct_planning_snapshot,
    validate_planning_snapshot,
)
from caa_scheduler.validation import validate_schedule


class V113BhmConnectivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_2"
            / "canonical_schedule.json"
        )
        cls.round_one_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_3_round_1.json"
        )
        cls.round_one = apply_optimization_overlay(
            cls.base,
            cls.round_one_overlay,
        )
        cls.round_two_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_3_round_2.json"
        )
        cls.round_two = apply_optimization_overlay(
            cls.round_one,
            cls.round_two_overlay,
        )
        cls.round_three_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_3_round_3.json"
        )
        cls.round_three = apply_optimization_overlay(
            cls.round_two,
            cls.round_three_overlay,
        )
        cls.round_four_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_3_round_4.json"
        )
        cls.candidate = apply_optimization_overlay(
            cls.round_three,
            cls.round_four_overlay,
        )
        cls.gates = export_gate_schedule(
            cls.candidate,
            rejoin_avoidable_tows=True,
        )

    def test_routes_form_the_bhm_focus_city_bank(self) -> None:
        expected = {
            117: ["MCI", "OMA", "MCI", "BHM", "SFB", "BHM", "MCI", "PIA"],
            128: ["TUL", "BHM", "PIE", "BHM", "DAB", "BHM", "HRL", "BHM", "SGF"],
            139: ["DAY", "TOL", "DAY", "BHM", "DAY", "SBN", "DAY", "TRI"],
            162: ["COU", "MCI", "CID", "MCI", "BHM", "MCI", "DSM"],
            138: ["HSV", "DAY", "MSN", "DAY", "TRI", "DAY", "BHM", "DAY"],
            715: ["SFB", "RDU", "SFB", "PHF", "BHM", "FLL", "BHM", "PHF"],
            524: ["SAT", "MCI", "BHM", "FLL", "BHM", "MCI"],
            102: ["ATW", "DAY", "ATW", "BHM", "ATW", "DAY", "AVL"],
            130: ["CID", "MCI", "ICT", "BHM", "ICT", "MCI", "CRP"],
            161: ["FAR", "MCI", "FSD", "BHM", "FSD", "MCI", "COU"],
            164: ["JAN", "MCI", "OMA", "BHM", "OMA", "MCI", "MAF"],
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

    def test_pie_sfb_and_fll_gain_bhm_round_trips(self) -> None:
        directed = Counter(
            (leg["origin"], leg["destination"])
            for leg in self.candidate["legs"]
        )
        for destination in ("PIE", "SFB"):
            self.assertEqual(directed[("BHM", destination)], 1)
            self.assertEqual(directed[(destination, "BHM")], 1)
        self.assertEqual(directed[("BHM", "FLL")], 2)
        self.assertEqual(directed[("FLL", "BHM")], 2)

        flp = {
            city["code"]
            for city in self.candidate["cities"]
            if city.get("group") == "FLP"
        }
        served = {
            leg["destination"]
            for leg in self.candidate["legs"]
            if leg["origin"] == "BHM" and leg["destination"] in flp
        }
        self.assertEqual(
            served,
            {"DAB", "EYW", "FLL", "PGD", "PIE", "SFB", "SRQ"},
        )

    def test_mci_and_day_feed_the_new_sfb_service(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        sfb_departure = legs["V113-R117-BHM-SFB"]["departureMinute"]
        self.assertEqual(
            sfb_departure - legs["V113-R117-MCI-BHM"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            sfb_departure - legs["V113-R139-DAY-BHM"]["arrivalMinute"],
            81,
        )
        self.assertEqual(
            legs["V113-R117-BHM-MCI"]["departureMinute"]
            - legs["V113-R117-SFB-BHM"]["arrivalMinute"],
            40,
        )

    def test_phf_and_day_connect_through_bhm_to_fll(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        self.assertEqual(
            legs["V113-R715-BHM-FLL"]["departureMinute"]
            - legs["V113-R715-PHF-BHM"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V113-R715-BHM-PHF"]["departureMinute"]
            - legs["V113-R715-FLL-BHM"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V113-R138-BHM-DAY"]["departureMinute"]
            - legs["V113-R715-FLL-BHM"]["arrivalMinute"],
            44,
        )

    def test_mci_feeds_the_second_fll_frequency(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        self.assertEqual(
            legs["V113-R524-BHM-FLL"]["departureMinute"]
            - legs["V113-R524-MCI-BHM"]["arrivalMinute"],
            123,
        )
        self.assertEqual(
            legs["V113-R524-BHM-MCI"]["departureMinute"]
            - legs["V113-R524-FLL-BHM"]["arrivalMinute"],
            40,
        )

    def test_long_hold_feeders_connect_with_flp_flying(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        self.assertEqual(
            legs["V113-R117-BHM-SFB"]["departureMinute"]
            - legs["V113-R164-OMA-BHM"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V113-R164-BHM-OMA"]["departureMinute"]
            - legs["V113-R715-FLL-BHM"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V113-R715-BHM-FLL"]["departureMinute"]
            - legs["V113-R102-ATW-BHM"]["arrivalMinute"],
            42,
        )
        self.assertEqual(
            legs["V113-R102-BHM-ATW"]["departureMinute"]
            - legs["BHM-PGD-CRJ700-01-IN"]["arrivalMinute"],
            81,
        )
        self.assertEqual(
            legs["V113-R524-BHM-FLL"]["departureMinute"]
            - legs["V113-R130-ICT-BHM"]["arrivalMinute"],
            119,
        )
        self.assertEqual(
            legs["V113-R130-BHM-ICT"]["departureMinute"]
            - legs["BHM-EYW-CRJ200-01-IN"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V113-R117-BHM-SFB"]["departureMinute"]
            - legs["V113-R161-FSD-BHM"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V113-R161-BHM-FSD"]["departureMinute"]
            - legs["BHM-PGD-CRJ700-01-IN"]["arrivalMinute"],
            40,
        )

    def test_only_declared_released_legs_are_retimed(self) -> None:
        declared = {
            item["legId"]
            for overlay in (
                self.round_one_overlay,
                self.round_four_overlay,
            )
            for item in overlay["retimeLegs"]
        }
        base = {leg["id"]: leg for leg in self.base["legs"]}
        candidate = {leg["id"]: leg for leg in self.candidate["legs"]}
        changed = {
            identifier
            for identifier, leg in base.items()
            if (
                leg["departureMinute"],
                leg["arrivalMinute"],
            )
            != (
                candidate[identifier]["departureMinute"],
                candidate[identifier]["arrivalMinute"],
            )
        }
        self.assertEqual(changed, declared)

    def test_round_two_does_not_retime_round_one_flying(self) -> None:
        before = {leg["id"]: leg for leg in self.round_one["legs"]}
        after = {leg["id"]: leg for leg in self.round_two["legs"]}
        for identifier, leg in before.items():
            self.assertEqual(
                (leg["departureMinute"], leg["arrivalMinute"]),
                (
                    after[identifier]["departureMinute"],
                    after[identifier]["arrivalMinute"],
                ),
            )

    def test_round_three_does_not_retime_prior_flying(self) -> None:
        before = {leg["id"]: leg for leg in self.round_two["legs"]}
        after = {leg["id"]: leg for leg in self.round_three["legs"]}
        for identifier, leg in before.items():
            self.assertEqual(
                (leg["departureMinute"], leg["arrivalMinute"]),
                (
                    after[identifier]["departureMinute"],
                    after[identifier]["arrivalMinute"],
                ),
            )

    def test_round_four_only_retimes_declared_prior_flying(self) -> None:
        declared = {
            item["legId"] for item in self.round_four_overlay["retimeLegs"]
        }
        before = {leg["id"]: leg for leg in self.round_three["legs"]}
        after = {leg["id"]: leg for leg in self.candidate["legs"]}
        changed = {
            identifier
            for identifier, leg in before.items()
            if (
                leg["departureMinute"],
                leg["arrivalMinute"],
            )
            != (
                after[identifier]["departureMinute"],
                after[identifier]["arrivalMinute"],
            )
        }
        self.assertEqual(changed, declared)

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
        self.assertEqual(len(self.candidate["legs"]), 998)
        self.assertEqual(len(stands), 29)
        self.assertEqual(
            sum(claim["end"] - claim["start"] for claim in stands),
            16822,
        )

    def test_only_release_is_exposed_and_is_the_app_default(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_3_feasibility_01", exposed)
        self.assertNotIn("schedule_7_v1_1_3_feasibility_02", exposed)
        self.assertNotIn("schedule_7_v1_1_3_feasibility_03", exposed)
        self.assertNotIn("schedule_7_v1_1_3_feasibility_04", exposed)
        self.assertIn("schedule_7_v1_1_3", exposed)
        self.assertEqual(manifest["schedules"][-1]["id"], "schedule_7_v1_1_3")
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_3")


if __name__ == "__main__":
    unittest.main()
