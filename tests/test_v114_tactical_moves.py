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


class V114TacticalMovesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_3"
            / "canonical_schedule.json"
        )
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_4_round_1.json"
        )
        cls.candidate = apply_optimization_overlay(cls.base, cls.overlay)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_reciprocal_pre_originators_exchange_aircraft(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        fll_position = legs["V114-R712-FLL-PHF"]
        phf_position = legs["V114-R716-PHF-FLL"]
        f1106 = legs["FLL-PHF-MAX9-03-IN"]
        f1112 = legs["FLL-PHF-MAX9-02-OUT"]

        self.assertEqual(
            (fll_position["departure"], fll_position["arrival"]),
            ("05:00", "07:03"),
        )
        self.assertEqual(f1106["departureMinute"] - fll_position["arrivalMinute"], 82)
        self.assertEqual(
            (phf_position["departure"], phf_position["arrival"]),
            ("06:05", "08:08"),
        )
        self.assertEqual(f1112["departureMinute"] - phf_position["arrivalMinute"], 42)

        self.assertEqual((f1106["route"], f1106["line"], f1106["day"]), (712, "A", 2))
        self.assertEqual((f1112["route"], f1112["line"], f1112["day"]), (716, "D", 1))

    def test_market_ceiling_is_preserved_with_productive_paths(self) -> None:
        directed = Counter(
            (leg["origin"], leg["destination"])
            for leg in self.candidate["legs"]
        )
        self.assertEqual(directed[("PHF", "FLL")], 6)
        self.assertEqual(directed[("FLL", "PHF")], 6)

        expected_paths = {
            703: ["SFB", "PHF", "BHM", "FLL", "MCI", "AUS", "MCI"],
            704: ["MCI", "AUS", "MCI", "SFB", "DAL", "MCI", "CLT"],
            705: ["CLT", "SFB", "PHF", "FLL", "SFB", "PHF", "FLL"],
        }
        for route, expected in expected_paths.items():
            route_legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [route_legs[0]["origin"], *[leg["destination"] for leg in route_legs]],
                expected,
            )

    def test_rotation_reclosure_does_not_add_an_aircraft_day(self) -> None:
        base_days = {
            (leg["line"], leg["day"])
            for leg in self.base["legs"]
            if leg["fleet"] == "MAX9"
        }
        candidate_days = {
            (leg["line"], leg["day"])
            for leg in self.candidate["legs"]
            if leg["fleet"] == "MAX9"
        }
        self.assertEqual(len(base_days), 21)
        self.assertEqual(len(candidate_days), 21)

    def test_candidate_passes_validation_and_fixed_inventory(self) -> None:
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
        phf = next(city for city in self.gates["cities"] if city["code"] == "PHF")
        self.assertEqual(len(self.candidate["legs"]), 1004)
        self.assertEqual(len({leg["route"] for leg in self.candidate["legs"]}), 179)
        self.assertEqual(len(stands), 29)
        self.assertEqual(sum(claim["end"] - claim["start"] for claim in stands), 16619)
        self.assertEqual(phf["peakUsed"], 20)
        self.assertEqual(
            sum(claim["rowType"] == "stand" for claim in phf["claims"]),
            8,
        )

    def test_overlay_is_deterministic_and_guarded(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.base, self.overlay),
        )
        stale = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_3"
            / "canonical_schedule.json"
        )
        leg = next(item for item in stale["legs"] if item["id"] == "FLL-PHF-MAX9-02-IN")
        leg["departureMinute"] += 1
        with self.assertRaisesRegex(ValueError, "Stale overlay"):
            apply_optimization_overlay(stale, self.overlay)

    def test_only_release_is_exposed_in_the_app(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_4_feasibility_01", exposed)
        self.assertIn("schedule_7_v1_1_4", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_4")


class V114TacticalRoundTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_3"
            / "canonical_schedule.json"
        )
        round_one_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_4_round_1.json"
        )
        cls.round_one = apply_optimization_overlay(base, round_one_overlay)
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_4_round_2.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_one, cls.overlay)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_extensions_match_the_identified_terminators(self) -> None:
        expected = {
            169: ["SBN", "DAY", "FWA", "SYR", "FWA", "DAY", "FWA"],
            122: ["PWM", "SYR", "SWF", "DAY", "SWF", "SYR", "SWF"],
        }
        for route, path in expected.items():
            route_legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [route_legs[0]["origin"], *[leg["destination"] for leg in route_legs]],
                path,
            )

        f1886 = next(leg for leg in self.candidate["legs"] if leg["flight"] == 1886)
        self.assertEqual(f1886["route"], 122)
        self.assertEqual((f1886["departure"], f1886["arrival"]), ("11:08", "11:57"))

    def test_new_turns_and_bank_exceptions_are_exact(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_times = {
            "V114-R169-FWA-SYR": ("12:20", "13:55"),
            "V114-R169-SYR-FWA": ("14:35", "16:10"),
            "V114-R169-FWA-DAY": ("16:50", "17:30"),
            "V114-R169-DAY-FWA": ("18:10", "18:50"),
            "V114-R122-SWF-DAY": ("12:37", "14:19"),
            "V114-R122-DAY-SWF": ("15:25", "17:07"),
            "V114-R122-SWF-SYR": ("18:41", "19:30"),
            "V114-R122-SYR-SWF": ("20:10", "20:59"),
        }
        for identifier, times in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                times,
            )

        self.assertEqual(
            legs["V114-R169-SYR-FWA"]["departureMinute"]
            - legs["V114-R169-FWA-SYR"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V114-R122-SYR-SWF"]["departureMinute"]
            - legs["V114-R122-SWF-SYR"]["arrivalMinute"],
            40,
        )

        operating = validate_operating_rules(self.candidate)
        hub_banks = next(
            check for check in operating["checks"] if check["id"] == "hub_bank_alignment"
        )
        self.assertEqual(hub_banks["status"], "overridden")
        self.assertEqual(hub_banks["metrics"]["overriddenFindingCount"], 2)
        self.assertEqual(hub_banks["metrics"]["effectiveFindingCount"], 0)

    def test_round_two_only_retimes_f1886(self) -> None:
        before = {leg["id"]: leg for leg in self.round_one["legs"]}
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
        self.assertEqual(changed, {"SWF-SYR-CRJ200-02-IN"})

    def test_round_two_passes_validation_without_more_aircraft_or_stands(self) -> None:
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

        crj200_days = {
            (leg["line"], leg["day"])
            for leg in self.candidate["legs"]
            if leg["fleet"] == "CRJ200"
        }
        stands = [
            claim
            for city in self.gates["cities"]
            for claim in city["claims"]
            if claim["rowType"] == "stand"
        ]
        self.assertEqual(len(self.candidate["legs"]), 1012)
        self.assertEqual(len(crj200_days), 76)
        self.assertEqual(len(stands), 29)
        self.assertEqual(sum(claim["end"] - claim["start"] for claim in stands), 16607)
        for code in ("FWA", "SWF"):
            city = next(city for city in self.gates["cities"] if city["code"] == code)
            self.assertFalse(any(claim["rowType"] == "stand" for claim in city["claims"]))

    def test_round_two_draft_remains_unpublished(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_4_feasibility_01", exposed)
        self.assertNotIn("schedule_7_v1_1_4_feasibility_02", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_4")


class V114TacticalRoundThreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidate = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_3"
            / "canonical_schedule.json"
        )
        for round_number in (1, 2):
            overlay = read_json(
                REPO_ROOT
                / "config"
                / "optimizations"
                / f"schedule_7_v1_1_4_round_{round_number}.json"
            )
            candidate = apply_optimization_overlay(candidate, overlay)
        cls.round_two = candidate
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_4_round_3.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_two, cls.overlay)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_each_mci_terminator_gains_the_selected_round_trip(self) -> None:
        expected_suffixes = {
            116: ["XNA", "MCI", "CAK", "MCI"],
            133: ["SDF", "MCI", "CLT", "MCI"],
            135: ["MFE", "MCI", "PNS", "MCI"],
            152: ["SBN", "MCI", "IND", "MCI"],
            344: ["HRL", "MCI", "MKE", "MCI"],
        }
        for route, expected in expected_suffixes.items():
            route_legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            path = [route_legs[0]["origin"], *[leg["destination"] for leg in route_legs]]
            self.assertEqual(path[-4:], expected)

    def test_new_flying_has_expected_times_and_market_frequencies(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_times = {
            "V114-R133-MCI-CLT": ("14:45", "18:04"),
            "V114-R133-CLT-MCI": ("18:44", "20:03"),
            "V114-R135-MCI-PNS": ("15:35", "17:45"),
            "V114-R135-PNS-MCI": ("18:25", "20:35"),
            "V114-R116-MCI-CAK": ("15:37", "18:42"),
            "V114-R116-CAK-MCI": ("19:40", "20:45"),
            "V114-R152-MCI-IND": ("16:25", "18:55"),
            "V114-R152-IND-MCI": ("19:35", "20:05"),
            "V114-R344-MCI-MKE": ("18:05", "19:30"),
            "V114-R344-MKE-MCI": ("20:10", "21:35"),
        }
        for identifier, times in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                times,
            )

        directed = Counter(
            (leg["origin"], leg["destination"])
            for leg in self.candidate["legs"]
        )
        self.assertEqual(directed[("MCI", "CLT")], 3)
        self.assertEqual(directed[("MCI", "PNS")], 3)
        self.assertEqual(directed[("MCI", "CAK")], 1)
        self.assertEqual(directed[("MCI", "IND")], 2)
        self.assertEqual(directed[("MCI", "MKE")], 4)

    def test_round_three_does_not_retime_existing_flying(self) -> None:
        before = {leg["id"]: leg for leg in self.round_two["legs"]}
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
        self.assertEqual(changed, set())
        self.assertFalse(self.overlay.get("operatingOverrides"))

    def test_round_three_passes_validation_and_removes_mci_stands(self) -> None:
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

        aircraft_days = Counter(
            fleet
            for line, day, fleet in {
                (leg["line"], leg["day"], leg["fleet"])
                for leg in self.candidate["legs"]
            }
        )
        stands = [
            claim
            for city in self.gates["cities"]
            for claim in city["claims"]
            if claim["rowType"] == "stand"
        ]
        mci = next(city for city in self.gates["cities"] if city["code"] == "MCI")
        self.assertEqual(len(self.candidate["legs"]), 1022)
        self.assertEqual(aircraft_days["CRJ200"], 76)
        self.assertEqual(aircraft_days["CRJ700"], 54)
        self.assertEqual(len(stands), 24)
        self.assertEqual(sum(claim["end"] - claim["start"] for claim in stands), 12888)
        self.assertEqual(mci["peakUsed"], 16)
        self.assertFalse(any(claim["rowType"] == "stand" for claim in mci["claims"]))

    def test_round_three_draft_is_replaced_by_the_release(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_4_feasibility_03", exposed)
        self.assertIn("schedule_7_v1_1_4", exposed)
        self.assertEqual(manifest["schedules"][-1]["id"], "schedule_7_v1_1_4")
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_4")


if __name__ == "__main__":
    unittest.main()
