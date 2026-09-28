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


class V115PhfExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_4"
            / "canonical_schedule.json"
        )
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_5_round_1.json"
        )
        cls.candidate = apply_optimization_overlay(cls.base, cls.overlay)
        cls.base_gates = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_4"
            / "gates.json"
        )
        cls.gates = export_gate_schedule(cls.candidate)

    def test_round_extends_exactly_the_five_early_phf_terminators(self) -> None:
        routes: dict[int, list[dict]] = {}
        for leg in self.base["legs"]:
            routes.setdefault(leg["route"], []).append(leg)
        early_terminators = {
            route
            for route, legs in routes.items()
            if (last := max(legs, key=lambda item: item["sequenceWithinRoute"]))[
                "destination"
            ]
            == "PHF"
            and last["arrivalMinute"] < 18 * 60 + 30
        }
        self.assertEqual(early_terminators, {718, 354, 329, 314, 328})
        self.assertEqual(
            {item["route"] for item in self.overlay["insertLegs"]},
            early_terminators,
        )

    def test_extensions_have_the_selected_paths_and_times(self) -> None:
        expected_paths = {
            718: ["RFD", "SFB", "PHF", "JAX", "PHF", "PIT", "PHF"],
            354: ["PHF", "PNS", "PHF", "ROC", "PHF", "RFD", "PHF"],
            329: ["PHF", "MSY", "PHF", "SAV", "PHF", "BDL", "PHF"],
            314: ["SAV", "PHF", "BNA", "PHF", "PWM", "PHF", "BWI", "PHF"],
            328: ["SDF", "JAX", "SYR", "CLT", "PHF", "GSP", "PHF"],
        }
        for route, expected in expected_paths.items():
            legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [legs[0]["origin"], *[leg["destination"] for leg in legs]],
                expected,
            )

        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_times = {
            "V115-R718-PHF-JAX": ("13:56", "15:32"),
            "V115-R718-JAX-PHF": ("16:50", "18:26"),
            "V115-R718-PHF-PIT": ("19:06", "20:15"),
            "V115-R718-PIT-PHF": ("20:55", "22:04"),
            "V115-R354-PHF-RFD": ("14:51", "15:57"),
            "V115-R354-RFD-PHF": ("19:08", "22:14"),
            "V115-R329-PHF-BDL": ("18:36", "19:56"),
            "V115-R329-BDL-PHF": ("20:36", "21:56"),
            "V115-R314-PHF-BWI": ("18:52", "19:40"),
            "V115-R314-BWI-PHF": ("20:44", "21:32"),
            "V115-R328-PHF-GSP": ("18:56", "20:11"),
            "V115-R328-GSP-PHF": ("20:51", "22:06"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

    def test_existing_mini_bank_is_repositioned_without_widening(self) -> None:
        base_bank = next(
            bank for bank in self.base["hubBanks"] if bank["id"] == "PHF-M6"
        )
        bank = next(
            bank for bank in self.candidate["hubBanks"] if bank["id"] == "PHF-M6"
        )
        self.assertEqual(
            (base_bank["startMinute"], base_bank["endMinute"]),
            (1185, 1205),
        )
        self.assertEqual((bank["startMinute"], bank["endMinute"]), (1132, 1192))
        self.assertEqual(bank["endMinute"] - bank["startMinute"], 60)

    def test_candidate_passes_validation_without_more_aircraft(self) -> None:
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
        self.assertEqual(len(self.candidate["legs"]), 1034)
        self.assertEqual(len({leg["route"] for leg in self.candidate["legs"]}), 179)
        self.assertEqual(len({leg["line"] for leg in self.candidate["legs"]}), 23)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_extensions_reduce_phf_and_systemwide_stand_use(self) -> None:
        def stand_metrics(gates: dict, code: str | None = None) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                if code is None or city["code"] == code
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.base_gates), (24, 12888))
        self.assertEqual(stand_metrics(self.gates), (21, 10320))
        self.assertEqual(stand_metrics(self.base_gates, "PHF"), (8, 4287))
        self.assertEqual(stand_metrics(self.gates, "PHF"), (5, 1719))

        base_phf = next(
            city for city in self.base_gates["cities"] if city["code"] == "PHF"
        )
        phf = next(city for city in self.gates["cities"] if city["code"] == "PHF")
        self.assertEqual((base_phf["peakUsed"], phf["peakUsed"]), (20, 18))

    def test_overlay_is_guarded_and_draft_is_not_exposed(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.base, self.overlay),
        )
        stale = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_4"
            / "canonical_schedule.json"
        )
        bank = next(item for item in stale["hubBanks"] if item["id"] == "PHF-M6")
        bank["startMinute"] += 1
        with self.assertRaisesRegex(ValueError, "Stale overlay"):
            apply_optimization_overlay(stale, self.overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_5_feasibility_01", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_5")


class V115SyrLateBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_4"
            / "canonical_schedule.json"
        )
        cls.round_one_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_5_round_1.json"
        )
        cls.round_one = apply_optimization_overlay(cls.base, cls.round_one_overlay)
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_5_round_2.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_one, cls.overlay)
        cls.round_one_gates = export_gate_schedule(cls.round_one)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_round_covers_the_seven_identified_syr_terminators(self) -> None:
        routes: dict[int, list[dict]] = {}
        for leg in self.round_one["legs"]:
            routes.setdefault(leg["route"], []).append(leg)
        early_terminators = {
            route
            for route, legs in routes.items()
            if (last := max(legs, key=lambda item: item["sequenceWithinRoute"]))[
                "destination"
            ]
            == "SYR"
            and last["arrivalMinute"] <= 19 * 60 + 19
        }
        self.assertEqual(early_terminators, {176, 321, 323, 515, 165, 306, 518})
        self.assertEqual(
            self.overlay["initiative"]["routes"],
            [176, 321, 323, 515, 165, 306, 518],
        )

    def test_late_bank_paths_and_bank_one_originators_are_exact(self) -> None:
        expected_paths = {
            176: ["SYR", "SWF", "SYR", "BNA", "SYR"],
            321: ["BNA", "SYR", "SRQ", "SYR", "PIT"],
            322: ["PIT", "SYR", "SRQ", "SYR", "SRQ"],
            323: ["SRQ", "SYR", "PHF", "SYR", "ABE"],
            324: ["ABE", "SYR", "SRQ", "SYR", "CLT", "BDL"],
            515: ["GSO", "RFD", "DSM", "RFD", "SYR", "RFD", "SYR", "ORH"],
            516: ["ORH", "SYR", "FLL", "SYR", "PIE", "PHF", "PIE"],
            165: ["FWA", "DAY", "ATW", "DAY", "CAK", "SYR", "ROC", "SYR"],
            306: ["CLT", "BDL", "CLT", "SYR", "BUF"],
            307: ["BUF", "SYR", "CLT", "PHF", "PIT", "PHF", "CHS"],
        }
        for route, expected in expected_paths.items():
            legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [legs[0]["origin"], *[leg["destination"] for leg in legs]],
                expected,
            )

        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_times = {
            "V115-R176-SYR-BNA": ("16:30", "17:40"),
            "V115-R176-BNA-SYR": ("18:20", "21:30"),
            "V115-R165-SYR-ROC": ("19:36", "20:15"),
            "V115-R165-ROC-SYR": ("20:55", "21:34"),
            "V115-R321-SYR-PIT": ("22:14", "23:20"),
            "V115-R322-PIT-SYR": ("04:30", "05:36"),
            "V115-R323-SYR-ABE": ("22:18", "23:10"),
            "V115-R324-ABE-SYR": ("04:30", "05:22"),
            "V115-R306-SYR-BUF": ("22:22", "23:09"),
            "V115-R307-BUF-SYR": ("04:30", "05:17"),
            "V115-R515-SYR-ORH": ("22:26", "23:24"),
            "V115-R516-ORH-SYR": ("04:30", "05:28"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

    def test_bank_windows_and_following_turns_are_legal(self) -> None:
        banks = {bank["id"]: bank for bank in self.candidate["hubBanks"]}
        self.assertEqual(
            (banks["SYR-B1"]["startMinute"], banks["SYR-B1"]["endMinute"]),
            (309, 369),
        )
        self.assertEqual(
            (banks["SYR-B7"]["startMinute"], banks["SYR-B7"]["endMinute"]),
            (1290, 1350),
        )
        self.assertEqual(self.candidate["operatingPolicy"]["hubBankCounts"]["SYR"], 7)

        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        turns = (
            ("V115-R324-ABE-SYR", "SRQ-SYR-CRJ700-03-IN"),
            ("V115-R307-BUF-SYR", "CLT-SYR-CRJ700-02-IN"),
            ("V115-R516-ORH-SYR", "FLL-SYR-CRJ900-02-IN"),
        )
        for inbound, outbound in turns:
            self.assertEqual(
                legs[outbound]["departureMinute"] - legs[inbound]["arrivalMinute"],
                40,
            )

        round_one_route_518 = [
            leg for leg in self.round_one["legs"] if leg["route"] == 518
        ]
        candidate_route_518 = [
            leg for leg in self.candidate["legs"] if leg["route"] == 518
        ]
        self.assertEqual(candidate_route_518, round_one_route_518)

    def test_candidate_passes_validation_and_ron_requirements(self) -> None:
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(
            any(
                check["hardStop"] and check["status"] == "fail"
                for check in operating["checks"]
            )
        )
        checks = {check["id"]: check for check in operating["checks"]}
        self.assertEqual(checks["rolling_ron_window"]["status"], "pass")
        self.assertEqual(checks["rolling_ron_grace"]["status"], "pass")
        self.assertEqual(checks["destination_ron_coverage"]["status"], "pass")
        self.assertEqual(
            checks["hub_bank_alignment"]["metrics"]["effectiveFindingCount"],
            0,
        )
        self.assertEqual(checks["minimum_turn_time"]["status"], "pass")

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
        self.assertEqual(len(self.candidate["legs"]), 1046)
        self.assertEqual(len({leg["route"] for leg in self.candidate["legs"]}), 179)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_round_reduces_syr_and_systemwide_stand_minutes(self) -> None:
        def stand_metrics(gates: dict, code: str | None = None) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                if code is None or city["code"] == code
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.round_one_gates), (21, 10320))
        self.assertEqual(stand_metrics(self.gates), (21, 8440))
        self.assertEqual(stand_metrics(self.round_one_gates, "SYR"), (6, 3315))
        self.assertEqual(stand_metrics(self.gates, "SYR"), (6, 1435))
        syr = next(city for city in self.gates["cities"] if city["code"] == "SYR")
        self.assertEqual(syr["peakUsed"], 18)

    def test_round_two_overlay_is_guarded_and_unpublished(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.round_one, self.overlay),
        )
        stale = apply_optimization_overlay(self.base, self.round_one_overlay)
        bank = next(item for item in stale["hubBanks"] if item["id"] == "SYR-B1")
        bank["startMinute"] += 1
        with self.assertRaisesRegex(ValueError, "Stale overlay"):
            apply_optimization_overlay(stale, self.overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_5_feasibility_02", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_5")


class V115AdditionalSyrFeedersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_4"
            / "canonical_schedule.json"
        )
        candidate = cls.base
        for filename in (
            "schedule_7_v1_1_5_round_1.json",
            "schedule_7_v1_1_5_round_2.json",
        ):
            overlay = read_json(
                REPO_ROOT / "config" / "optimizations" / filename
            )
            candidate = apply_optimization_overlay(candidate, overlay)
        cls.round_two = candidate
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_5_round_3.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_two, cls.overlay)
        cls.round_two_gates = export_gate_schedule(cls.round_two)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_three_terminators_feed_bank_seven_and_return_to_ron_cities(self) -> None:
        expected_paths = {
            144: [
                "MYR",
                "PHF",
                "SYR",
                "ROC",
                "SYR",
                "PWM",
                "SYR",
                "BUF",
                "SYR",
                "PWM",
            ],
            150: ["GRR", "DAY", "LEX", "DAY", "SYR", "ALB", "SYR", "ALB"],
            124: [
                "ILM",
                "PHF",
                "MDT",
                "SYR",
                "HPN",
                "SYR",
                "HVN",
                "SYR",
                "HVN",
            ],
        }
        for route, expected in expected_paths.items():
            legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [legs[0]["origin"], *[leg["destination"] for leg in legs]],
                expected,
            )

        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_times = {
            "V115-R144-PWM-SYR": ("17:37", "18:45"),
            "V115-R144-SYR-BUF": ("19:25", "20:11"),
            "V115-R144-BUF-SYR": ("20:51", "21:37"),
            "V115-R144-SYR-PWM": ("22:20", "23:28"),
            "V115-R150-ALB-SYR": ("20:46", "21:30"),
            "V115-R150-SYR-ALB": ("22:10", "22:54"),
            "V115-R124-HVN-SYR": ("20:34", "21:30"),
            "V115-R124-SYR-HVN": ("22:12", "23:08"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

        self.assertEqual(
            legs["V115-R144-SYR-BUF"]["departureMinute"]
            - legs["V115-R144-PWM-SYR"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V115-R144-BUF-SYR"]["departureMinute"]
            - legs["V115-R144-SYR-BUF"]["arrivalMinute"],
            40,
        )
        self.assertEqual(
            legs["V115-R144-SYR-PWM"]["departureMinute"]
            - legs["V115-R144-BUF-SYR"]["arrivalMinute"],
            43,
        )

    def test_bank_seven_has_five_feeders_and_seven_departures(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        bank_seven = [
            assignment
            for assignment in self.candidate["bankAssignments"]
            if assignment["bankId"] == "SYR-B7"
        ]
        arrivals = [
            legs[item["legId"]]
            for item in bank_seven
            if item["operation"] == "arrival"
        ]
        departures = [
            legs[item["legId"]]
            for item in bank_seven
            if item["operation"] == "departure"
        ]
        self.assertEqual(len(arrivals), 5)
        self.assertEqual(len(departures), 7)
        self.assertEqual(
            sorted(leg["departure"] for leg in departures),
            ["22:10", "22:12", "22:14", "22:18", "22:20", "22:22", "22:26"],
        )

    def test_supporting_retimes_release_the_bank_six_gate(self) -> None:
        before = {leg["id"]: leg for leg in self.round_two["legs"]}
        after = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected = {
            "SRQ-SYR-CRJ700-01-IN": (("19:05", "22:01"), ("18:45", "21:41")),
            "PWM-SYR-CRJ200-01-IN": (("19:35", "20:43"), ("19:00", "20:08")),
        }
        changed = {
            identifier
            for identifier in before
            if (
                before[identifier]["departureMinute"],
                before[identifier]["arrivalMinute"],
            )
            != (
                after[identifier]["departureMinute"],
                after[identifier]["arrivalMinute"],
            )
        }
        self.assertEqual(changed, set(expected))
        for identifier, (old_times, new_times) in expected.items():
            self.assertEqual(
                (before[identifier]["departure"], before[identifier]["arrival"]),
                old_times,
            )
            self.assertEqual(
                (after[identifier]["departure"], after[identifier]["arrival"]),
                new_times,
            )

    def test_candidate_passes_validation_without_new_section_26_findings(self) -> None:
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        checks = {check["id"]: check for check in operating["checks"]}
        self.assertEqual(checks["section_26_pairing_spacing"]["status"], "pass")
        self.assertEqual(checks["minimum_turn_time"]["status"], "pass")
        self.assertEqual(checks["rolling_ron_window"]["status"], "pass")
        self.assertEqual(
            checks["hub_bank_alignment"]["metrics"]["effectiveFindingCount"],
            0,
        )

        previous = {
            check["id"]: check
            for check in validate_operating_rules(self.round_two)["checks"]
        }
        self.assertEqual(
            {
                finding["id"]
                for finding in checks["section_26_city_departure_gap"]["findings"]
            },
            {
                finding["id"]
                for finding in previous["section_26_city_departure_gap"]["findings"]
            },
        )
        planning = reconstruct_planning_snapshot(self.candidate)
        self.assertEqual(
            validate_planning_snapshot(planning, self.candidate)["status"],
            "pass",
        )

    def test_round_preserves_aircraft_and_stand_metrics(self) -> None:
        def stand_metrics(gates: dict, code: str | None = None) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                if code is None or city["code"] == code
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.round_two_gates), (21, 8440))
        self.assertEqual(stand_metrics(self.gates), (21, 8440))
        self.assertEqual(stand_metrics(self.gates, "SYR"), (6, 1435))
        syr = next(city for city in self.gates["cities"] if city["code"] == "SYR")
        self.assertEqual(syr["peakUsed"], 18)

        aircraft_days = Counter(
            fleet
            for line, day, fleet in {
                (leg["line"], leg["day"], leg["fleet"])
                for leg in self.candidate["legs"]
            }
        )
        self.assertEqual(len(self.candidate["legs"]), 1054)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_round_three_overlay_is_guarded_and_unpublished(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.round_two, self.overlay),
        )
        stale_overlay = {
            **self.overlay,
            "retimeLegs": [
                {
                    **self.overlay["retimeLegs"][0],
                    "expectedDepartureMinute": 1144,
                },
                *self.overlay["retimeLegs"][1:],
            ],
        }
        with self.assertRaisesRegex(ValueError, "Stale overlay"):
            apply_optimization_overlay(self.round_two, stale_overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_5_feasibility_03", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_5")


class V115WesternHoldUtilizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_4"
            / "canonical_schedule.json"
        )
        candidate = cls.base
        for filename in (
            "schedule_7_v1_1_5_round_1.json",
            "schedule_7_v1_1_5_round_2.json",
            "schedule_7_v1_1_5_round_3.json",
        ):
            overlay = read_json(
                REPO_ROOT / "config" / "optimizations" / filename
            )
            candidate = apply_optimization_overlay(candidate, overlay)
        cls.round_three = candidate
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_5_round_4.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_three, cls.overlay)
        cls.round_three_gates = export_gate_schedule(cls.round_three)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_extensions_fill_the_three_identified_day_holds(self) -> None:
        expected_paths = {
            158: [
                "OMA",
                "MCI",
                "LIT",
                "MCI",
                "RFD",
                "MCI",
                "MKE",
                "MCI",
                "DSM",
            ],
            165: [
                "FWA",
                "DAY",
                "ATW",
                "MCI",
                "ATW",
                "DAY",
                "CAK",
                "SYR",
                "ROC",
                "SYR",
            ],
            309: ["CLT", "PHF", "MCI", "RFD", "MCI", "MEM"],
        }
        for route, expected in expected_paths.items():
            legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            self.assertEqual(
                [legs[0]["origin"], *[leg["destination"] for leg in legs]],
                expected,
            )

        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_times = {
            "V115-R165-ATW-MCI": ("07:32", "09:04"),
            "V115-R165-MCI-ATW": ("09:45", "11:17"),
            "V115-R158-MCI-RFD": ("11:25", "12:42"),
            "V115-R158-RFD-MCI": ("13:28", "14:45"),
            "V115-R158-MCI-MKE": ("15:28", "16:56"),
            "V115-R158-MKE-MCI": ("17:36", "19:04"),
            "V115-R309-MCI-RFD": ("13:06", "14:21"),
            "V115-R309-RFD-MCI": ("16:00", "17:15"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

    def test_round_adds_664_block_minutes_and_reduces_original_holds(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        added = [legs[item["id"]] for item in self.overlay["insertLegs"]]
        self.assertEqual(
            sum(leg["arrivalMinute"] - leg["departureMinute"] for leg in added),
            664,
        )

        self.assertEqual(
            (685 - 640) + (928 - 885) + (1195 - 1144),
            139,
        )
        self.assertEqual((452 - 369) + (795 - 677), 201)
        self.assertEqual((786 - 742) + (1135 - 1035), 144)

    def test_rfd_frequency_and_spacing_are_deliberate(self) -> None:
        departures = sorted(
            leg["departure"]
            for leg in self.candidate["legs"]
            if leg["origin"] == "MCI" and leg["destination"] == "RFD"
        )
        returns = sorted(
            leg["departure"]
            for leg in self.candidate["legs"]
            if leg["origin"] == "RFD" and leg["destination"] == "MCI"
        )
        self.assertEqual(departures, ["11:25", "13:06", "19:00"])
        self.assertEqual(returns, ["13:28", "16:00", "17:05"])

        operating = validate_operating_rules(self.candidate)
        checks = {check["id"]: check for check in operating["checks"]}
        self.assertEqual(checks["section_26_pairing_spacing"]["status"], "pass")

    def test_candidate_passes_validation_without_more_capacity(self) -> None:
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        checks = {check["id"]: check for check in operating["checks"]}
        self.assertEqual(checks["minimum_turn_time"]["status"], "pass")
        self.assertEqual(checks["rolling_ron_window"]["status"], "pass")
        self.assertEqual(
            checks["hub_bank_alignment"]["metrics"]["effectiveFindingCount"],
            0,
        )

        previous = {
            check["id"]: check
            for check in validate_operating_rules(self.round_three)["checks"]
        }
        current_city_gaps = {
            finding["id"]
            for finding in checks["section_26_city_departure_gap"]["findings"]
        }
        previous_city_gaps = {
            finding["id"]
            for finding in previous["section_26_city_departure_gap"]["findings"]
        }
        self.assertEqual(previous_city_gaps - current_city_gaps, {"ATW"})
        self.assertFalse(current_city_gaps - previous_city_gaps)
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
        self.assertEqual(len(self.candidate["legs"]), 1062)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_gate_and_stand_use_remain_unchanged(self) -> None:
        def stand_metrics(gates: dict) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.round_three_gates), (21, 8440))
        self.assertEqual(stand_metrics(self.gates), (21, 8440))
        mci = next(city for city in self.gates["cities"] if city["code"] == "MCI")
        atw = next(city for city in self.gates["cities"] if city["code"] == "ATW")
        self.assertEqual((mci["peakUsed"], atw["peakUsed"]), (16, 2))
        self.assertFalse(any(claim["rowType"] == "stand" for claim in mci["claims"]))
        self.assertFalse(any(claim["rowType"] == "stand" for claim in atw["claims"]))

    def test_round_four_overlay_is_guarded_and_unpublished(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.round_three, self.overlay),
        )
        stale = apply_optimization_overlay(
            self.base,
            read_json(
                REPO_ROOT
                / "config"
                / "optimizations"
                / "schedule_7_v1_1_5_round_1.json"
            ),
        )
        with self.assertRaisesRegex(ValueError, "expects base schedule"):
            apply_optimization_overlay(stale, self.overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_5_feasibility_04", exposed)
        self.assertIn("schedule_7_v1_1_5", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_5")


if __name__ == "__main__":
    unittest.main()
