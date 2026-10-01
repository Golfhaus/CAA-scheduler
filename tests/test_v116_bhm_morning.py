from __future__ import annotations

import copy
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


@unittest.skip("Superseded schedule or feasibility checkpoint; regression targets the latest release")
class V116BhmMorningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_5"
            / "canonical_schedule.json"
        )
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_6_round_1.json"
        )
        cls.candidate = apply_optimization_overlay(cls.base, cls.overlay)
        cls.base_gates = export_gate_schedule(cls.base)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_three_late_originators_gain_bhm_round_trips(self) -> None:
        expected_paths = {
            306: ["CLT", "BHM", "CLT", "BDL", "CLT", "SYR", "BUF"],
            339: ["SAV", "BHM", "SAV", "PHF", "CHS", "PHF", "CHS"],
            149: ["DAY", "BHM", "DAY", "HOU", "DAY", "GRR"],
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
            "V116-R306-CLT-BHM": ("04:30", "04:45"),
            "V116-R306-BHM-CLT": ("07:40", "10:55"),
            "V116-R339-SAV-BHM": ("04:30", "04:43"),
            "V116-R339-BHM-SAV": ("07:45", "09:58"),
            "V116-R149-DAY-BHM": ("04:30", "05:01"),
            "V116-R149-BHM-DAY": ("07:32", "10:03"),
            "DAY-HOU-CRJ200-03-OUT": ("11:15", "12:53"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

        self.assertEqual(
            legs["DAY-HOU-CRJ200-03-IN"]["departureMinute"]
            - legs["DAY-HOU-CRJ200-03-OUT"]["arrivalMinute"],
            67,
        )

    def test_bwi_candidate_is_deferred_without_changing_route_331(self) -> None:
        base_route = [leg for leg in self.base["legs"] if leg["route"] == 331]
        candidate_route = [
            leg for leg in self.candidate["legs"] if leg["route"] == 331
        ]
        self.assertEqual(candidate_route, base_route)
        self.assertFalse(
            any(leg["id"].startswith("V116-R331-") for leg in self.candidate["legs"])
        )
        deferred = self.overlay["initiative"]["evaluatedButDeferred"]
        self.assertEqual([(item["route"], item["city"]) for item in deferred], [(331, "BWI")])

    def test_new_flights_connect_both_directions_across_bhm_wave(self) -> None:
        arrivals = [
            leg for leg in self.candidate["legs"] if leg["destination"] == "BHM"
        ]
        departures = [
            leg for leg in self.candidate["legs"] if leg["origin"] == "BHM"
        ]

        def outbound_connections(arrival: dict) -> set[str]:
            return {
                departure["destination"]
                for departure in departures
                if 30
                <= departure["departureMinute"] - arrival["arrivalMinute"]
                <= 240
            }

        def inbound_connections(departure: dict) -> set[str]:
            return {
                arrival["origin"]
                for arrival in arrivals
                if 30
                <= departure["departureMinute"] - arrival["arrivalMinute"]
                <= 240
            }

        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected_outbound = {"MCI", "LBB", "SRQ", "PIE", "AUS", "DAL", "FLL"}
        for identifier in (
            "V116-R306-CLT-BHM",
            "V116-R339-SAV-BHM",
            "V116-R149-DAY-BHM",
        ):
            self.assertTrue(
                expected_outbound.issubset(outbound_connections(legs[identifier]))
            )

        expected_inbound = {"SGF", "XNA", "TUL", "HOU", "OKC"}
        for identifier in (
            "V116-R306-BHM-CLT",
            "V116-R339-BHM-SAV",
            "V116-R149-BHM-DAY",
        ):
            self.assertTrue(
                expected_inbound.issubset(inbound_connections(legs[identifier]))
            )

    def test_candidate_passes_validation_without_more_aircraft_or_section_26(self) -> None:
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
        self.assertEqual(checks["minimum_turn_time"]["status"], "pass")
        self.assertEqual(checks["fixed_physical_inventory"]["status"], "pass")
        self.assertEqual(checks["passenger_touch_on_stand"]["status"], "pass")

        previous = {
            check["id"]: check
            for check in validate_operating_rules(self.base)["checks"]
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
        aircraft_days = Counter(
            fleet
            for line, day, fleet in {
                (leg["line"], leg["day"], leg["fleet"])
                for leg in self.candidate["legs"]
            }
        )
        self.assertEqual(len(self.candidate["legs"]), 1068)
        self.assertEqual(len({leg["route"] for leg in self.candidate["legs"]}), 179)
        self.assertEqual(len({leg["line"] for leg in self.candidate["legs"]}), 23)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_bhm_holds_fit_and_reduce_total_stand_minutes(self) -> None:
        def stand_metrics(gates: dict, code: str | None = None) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                if code is None or city["code"] == code
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.base_gates), (21, 8440))
        self.assertEqual(stand_metrics(self.gates), (24, 8134))
        self.assertEqual(stand_metrics(self.gates, "BHM"), (4, 290))

        bhm = next(city for city in self.gates["cities"] if city["code"] == "BHM")
        self.assertEqual((bhm["nGates"], bhm["nStands"], bhm["peakUsed"]), (6, 4, 8))
        holds = {
            int(claim["label"]): (claim["start"], claim["end"])
            for claim in bhm["claims"]
            if claim["rowType"] == "stand" and claim["label"] in {"149", "306", "339"}
        }
        self.assertEqual(holds, {149: (346, 392), 306: (330, 400), 339: (328, 405)})

    def test_overlay_is_guarded_and_draft_is_not_exposed(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.base, self.overlay),
        )
        stale = copy.deepcopy(self.base)
        leg = next(
            item for item in stale["legs"] if item["id"] == "DAY-HOU-CRJ200-03-OUT"
        )
        leg["departureMinute"] += 1
        with self.assertRaisesRegex(ValueError, "Stale overlay"):
            apply_optimization_overlay(stale, self.overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_6_feasibility_01", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_6")


@unittest.skip("Superseded schedule or feasibility checkpoint; regression targets the latest release")
class V116IndependentTerminatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_5"
            / "canonical_schedule.json"
        )
        cls.round_one_overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_6_round_1.json"
        )
        cls.round_one = apply_optimization_overlay(
            cls.base,
            cls.round_one_overlay,
        )
        cls.overlay = read_json(
            REPO_ROOT
            / "config"
            / "optimizations"
            / "schedule_7_v1_1_6_round_2.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_one, cls.overlay)
        cls.round_one_gates = export_gate_schedule(cls.round_one)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_each_early_terminator_gets_its_selected_round_trip(self) -> None:
        expected_paths = {
            148: ["MHT", "SYR", "ROC", "DAY", "TYS", "DAY", "RFD", "DAY"],
            525: ["MCI", "RDU", "MCI", "SAT", "SFB", "SAT"],
            346: ["MCI", "BHM", "MCI", "HRL", "AUS", "HRL"],
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
            "V116-R148-DAY-RFD": ("17:30", "17:39"),
            "V116-R148-RFD-DAY": ("18:19", "20:28"),
            "V116-R525-SAT-SFB": ("16:45", "20:20"),
            "V116-R525-SFB-SAT": ("21:00", "22:35"),
            "V116-R346-HRL-AUS": ("17:02", "18:07"),
            "V116-R346-AUS-HRL": ("18:47", "19:52"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

        self.assertEqual(
            self.overlay["expectedCheckpoint"]["productiveBlockMinutesAdded"],
            578,
        )

    def test_extensions_preserve_following_aircraft_days(self) -> None:
        for route in (149, 526, 347):
            before = [leg for leg in self.round_one["legs"] if leg["route"] == route]
            after = [leg for leg in self.candidate["legs"] if leg["route"] == route]
            self.assertEqual(after, before)

        final_locations = {}
        for route in (148, 525, 346):
            legs = sorted(
                (leg for leg in self.candidate["legs"] if leg["route"] == route),
                key=lambda leg: leg["sequenceWithinRoute"],
            )
            final_locations[route] = legs[-1]["destination"]
        self.assertEqual(final_locations, {148: "DAY", 525: "SAT", 346: "HRL"})

    def test_route_148_start_is_constrained_by_day_gate_capacity(self) -> None:
        earlier = copy.deepcopy(self.overlay)
        earlier["schedule"] = {
            **earlier["schedule"],
            "id": "schedule_7_v1_1_6_gate_probe",
        }
        replacements = {
            "V116-R148-DAY-RFD": (1045, 1054),
            "V116-R148-RFD-DAY": (1094, 1223),
        }
        for leg in earlier["insertLegs"]:
            if leg["id"] in replacements:
                leg["departureMinute"], leg["arrivalMinute"] = replacements[leg["id"]]
        probe = apply_optimization_overlay(self.round_one, earlier)
        checks = {
            check["id"]: check for check in validate_operating_rules(probe)["checks"]
        }
        self.assertEqual(checks["passenger_touch_on_stand"]["status"], "fail")
        self.assertEqual(checks["fixed_physical_inventory"]["status"], "fail")

    def test_candidate_passes_without_new_overrides_or_section_26_findings(self) -> None:
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
        for identifier in (
            "departure_windows",
            "minimum_turn_time",
            "point_to_point_share",
            "section_26_pairing_spacing",
            "gate_assignment_conflicts",
            "passenger_touch_on_stand",
            "stand_capacity",
            "combined_capacity_peak",
            "fixed_physical_inventory",
        ):
            self.assertEqual(checks[identifier]["status"], "pass")

        previous = {
            check["id"]: check
            for check in validate_operating_rules(self.round_one)["checks"]
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
        aircraft_days = Counter(
            fleet
            for line, day, fleet in {
                (leg["line"], leg["day"], leg["fleet"])
                for leg in self.candidate["legs"]
            }
        )
        self.assertEqual(len(self.candidate["legs"]), 1074)
        self.assertEqual(len({leg["route"] for leg in self.candidate["legs"]}), 179)
        self.assertEqual(len({leg["line"] for leg in self.candidate["legs"]}), 23)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_round_removes_the_day_stand_hold(self) -> None:
        def stand_metrics(gates: dict, code: str | None = None) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                if code is None or city["code"] == code
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.round_one_gates), (24, 8134))
        self.assertEqual(stand_metrics(self.gates), (23, 7461))
        self.assertEqual(stand_metrics(self.round_one_gates, "DAY"), (1, 673))
        self.assertEqual(stand_metrics(self.gates, "DAY"), (0, 0))

        expected_peaks = {
            "DAY": 16,
            "RFD": 5,
            "SAT": 3,
            "SFB": 5,
            "HRL": 2,
            "AUS": 3,
        }
        actual_peaks = {
            city["code"]: city["peakUsed"]
            for city in self.gates["cities"]
            if city["code"] in expected_peaks
        }
        self.assertEqual(actual_peaks, expected_peaks)

    def test_round_two_overlay_is_guarded_and_unpublished(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.round_one, self.overlay),
        )
        stale = copy.deepcopy(self.round_one)
        stale["schedule"]["id"] = "schedule_7_v1_1_5"
        with self.assertRaisesRegex(ValueError, "Overlay expects base schedule"):
            apply_optimization_overlay(stale, self.overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_6_feasibility_02", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_6")


@unittest.skip("Superseded schedule or feasibility checkpoint; regression targets the latest release")
class V116PhfEarlyHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_5"
            / "canonical_schedule.json"
        )
        candidate = cls.base
        for filename in (
            "schedule_7_v1_1_6_round_1.json",
            "schedule_7_v1_1_6_round_2.json",
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
            / "schedule_7_v1_1_6_round_3.json"
        )
        cls.candidate = apply_optimization_overlay(cls.round_two, cls.overlay)
        cls.round_two_gates = export_gate_schedule(cls.round_two)
        cls.gates = export_gate_schedule(cls.candidate)

    def test_three_routes_gain_the_approved_early_round_trips(self) -> None:
        expected_paths = {
            330: [
                "PHF",
                "DAY",
                "PHF",
                "BWI",
                "PHF",
                "BWI",
                "BHM",
                "PHF",
                "BWI",
            ],
            338: ["PHF", "SYR", "PHF", "PVD", "PHF", "SAV"],
            719: ["PHF", "JAX", "PHF", "SFB", "CLT", "MCI", "HOU", "MCI", "BNA"],
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
            "V116-R330-PHF-DAY": ("04:30", "05:59"),
            "V116-R330-DAY-PHF": ("06:51", "08:20"),
            "V116-R338-PHF-SYR": ("04:30", "05:53"),
            "V116-R338-SYR-PHF": ("07:02", "08:25"),
            "V116-R719-PHF-JAX": ("04:30", "06:06"),
            "V116-R719-JAX-PHF": ("06:46", "08:22"),
        }
        for identifier, expected in expected_times.items():
            self.assertEqual(
                (legs[identifier]["departure"], legs[identifier]["arrival"]),
                expected,
            )

    def test_returns_preserve_the_approved_originator_margins(self) -> None:
        legs = {leg["id"]: leg for leg in self.candidate["legs"]}
        expected = {
            330: ("V116-R330-DAY-PHF", "BWI-PHF-CRJ700-01-IN", 55, 15),
            338: ("V116-R338-SYR-PHF", "PHF-PVD-CRJ700-03-OUT", 50, 10),
            719: ("V116-R719-JAX-PHF", "PHF-SFB-MAX9-01-OUT", 48, 8),
        }
        for route, (return_id, originator_id, turn, margin) in expected.items():
            actual_turn = (
                legs[originator_id]["departureMinute"]
                - legs[return_id]["arrivalMinute"]
            )
            self.assertEqual(actual_turn, turn, route)
            self.assertEqual(actual_turn - 40, margin, route)

        self.assertEqual(
            self.overlay["expectedCheckpoint"]["productiveBlockMinutesAdded"],
            536,
        )

    def test_only_the_approved_new_bank_exceptions_are_added(self) -> None:
        expected = {
            "V116-R330-DAY-PHF-departure",
            "V116-R330-DAY-PHF-arrival",
            "V116-R338-SYR-PHF-departure",
            "V116-R719-JAX-PHF-arrival",
        }
        self.assertEqual(
            {item["findingId"] for item in self.overlay["operatingOverrides"]},
            expected,
        )

        operating = validate_operating_rules(self.candidate)
        checks = {check["id"]: check for check in operating["checks"]}
        bank = checks["hub_bank_alignment"]
        self.assertEqual(bank["status"], "overridden")
        self.assertEqual(bank["metrics"]["effectiveFindingCount"], 0)
        current_findings = {finding["id"] for finding in bank["findings"]}
        self.assertTrue(expected.issubset(current_findings))
        for finding in bank["findings"]:
            if finding["id"] in expected:
                self.assertIn("override", finding)

    def test_candidate_passes_without_new_section_26_findings(self) -> None:
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
        for identifier in (
            "departure_windows",
            "minimum_turn_time",
            "section_26_pairing_spacing",
            "gate_assignment_conflicts",
            "passenger_touch_on_stand",
            "stand_capacity",
            "combined_capacity_peak",
            "fixed_physical_inventory",
        ):
            self.assertEqual(checks[identifier]["status"], "pass")

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
        aircraft_days = Counter(
            fleet
            for line, day, fleet in {
                (leg["line"], leg["day"], leg["fleet"])
                for leg in self.candidate["legs"]
            }
        )
        self.assertEqual(len(self.candidate["legs"]), 1080)
        self.assertEqual(len({leg["route"] for leg in self.candidate["legs"]}), 179)
        self.assertEqual(len({leg["line"] for leg in self.candidate["legs"]}), 23)
        self.assertEqual(
            aircraft_days,
            Counter({"CRJ200": 76, "CRJ700": 54, "CRJ900": 28, "MAX9": 21}),
        )

    def test_round_reduces_phf_and_systemwide_stand_use(self) -> None:
        def stand_metrics(gates: dict, code: str | None = None) -> tuple[int, int]:
            claims = [
                claim
                for city in gates["cities"]
                if code is None or city["code"] == code
                for claim in city["claims"]
                if claim["rowType"] == "stand"
            ]
            return len(claims), sum(claim["end"] - claim["start"] for claim in claims)

        self.assertEqual(stand_metrics(self.round_two_gates), (23, 7461))
        self.assertEqual(stand_metrics(self.gates), (21, 6188))
        self.assertEqual(stand_metrics(self.round_two_gates, "PHF"), (5, 1719))
        self.assertEqual(stand_metrics(self.gates, "PHF"), (3, 446))

        expected_peaks = {"PHF": 18, "DAY": 16, "SYR": 18, "JAX": 16}
        actual_peaks = {
            city["code"]: city["peakUsed"]
            for city in self.gates["cities"]
            if city["code"] in expected_peaks
        }
        self.assertEqual(actual_peaks, expected_peaks)

    def test_round_three_overlay_is_guarded_and_unpublished(self) -> None:
        self.assertEqual(
            self.candidate,
            apply_optimization_overlay(self.round_two, self.overlay),
        )
        stale = copy.deepcopy(self.round_two)
        stale["schedule"]["id"] = "schedule_7_v1_1_6_feasibility_01"
        with self.assertRaisesRegex(ValueError, "Overlay expects base schedule"):
            apply_optimization_overlay(stale, self.overlay)

        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        exposed = {schedule["id"] for schedule in manifest["schedules"]}
        self.assertNotIn("schedule_7_v1_1_6_feasibility_03", exposed)
        self.assertIn("schedule_7_v1_1_6", exposed)
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_1_6")


if __name__ == "__main__":
    unittest.main()
