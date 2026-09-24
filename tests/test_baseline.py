from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.baseline import build_baseline
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.gates import (
    GateCapacityError,
    GateClaim,
    _bounded_coloring,
    _greedy_coloring,
    assign_gates,
    build_claims,
    overlaps,
    serialize_assignments,
)
from caa_scheduler.importer import import_canonical_schedule
from caa_scheduler.io import read_json
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.timetable import export_timetable
from caa_scheduler.validation import validate_schedule


FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "schedule_6_v2_2_5"
WORKBOOK = FIXTURE_ROOT / "source" / "Schedule_6__Version_2_2_5.xlsx"
CITY_INFORMATION = FIXTURE_ROOT / "source" / "city_information_v2.csv"
EXPECTED_TIMETABLE = FIXTURE_ROOT / "expected" / "schedule_6_v2_2_5.json"
EXPECTED_GATE = FIXTURE_ROOT / "expected" / "gate_sked6_v2_2_5.json"
OPERATING_POLICY = REPO_ROOT / "config" / "policies" / "operating_rules_v2_0.json"
SCHEDULE = {
    "id": "schedule_6_v2_2_5",
    "number": 6,
    "version": "2.2.5",
    "label": "Schedule 6, Version 2.2.5 (in progress -- not yet Finalized)",
    "status": "in_progress",
    "fleetCounts": {
        "MAX9": 35,
        "CRJ900": 45,
        "CRJ700": 65,
        "CRJ200": 80,
    },
}
CONNECTION_WINDOW = {"minimum": 30, "maximum": 240}
GATE_PLAN = {
    "label": "Schedule 6, Version 2.2.5",
    "forcedStandSplits": {"BHM": ["103 -> 103"]},
}


class ScheduleSixBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = import_canonical_schedule(
            workbook_path=WORKBOOK,
            city_information_path=CITY_INFORMATION,
            schedule=SCHEDULE,
            connection_window=CONNECTION_WINDOW,
            gate_plan=GATE_PLAN,
            gate_baseline_path=EXPECTED_GATE,
            operating_policy_path=OPERATING_POLICY,
        )

    def test_import_preserves_golden_counts(self) -> None:
        self.assertEqual(len(self.canonical["legs"]), 1383)
        self.assertEqual(len(self.canonical["cities"]), 105)
        self.assertEqual(len({leg["route"] for leg in self.canonical["legs"]}), 225)
        self.assertEqual(len({leg["line"] for leg in self.canonical["legs"]}), 20)

    def test_timetable_export_matches_v2_2_5_exactly(self) -> None:
        expected = read_json(EXPECTED_TIMETABLE)
        self.assertEqual(export_timetable(self.canonical), expected)

    def test_published_timetable_is_flight_number_ordered(self) -> None:
        flights = export_timetable(self.canonical)["flights"]
        self.assertEqual(
            [flight["flight"] for flight in flights],
            sorted(flight["flight"] for flight in flights),
        )

    def test_gate_export_matches_v2_2_5_exactly(self) -> None:
        self.assertEqual(export_gate_schedule(self.canonical), read_json(EXPECTED_GATE))

    def test_gate_baseline_preserves_subminute_and_overnight_times(self) -> None:
        by_flight = {leg["flight"]: leg for leg in self.canonical["legs"]}
        self.assertEqual(by_flight[2495]["arrivalMinute"], 1520.0)
        self.assertTrue(
            any(
                isinstance(leg["arrivalMinute"], float)
                and not leg["arrivalMinute"].is_integer()
                for leg in self.canonical["legs"]
            )
        )

    def test_cyclic_overlap_detects_midnight_conflict(self) -> None:
        late = GateClaim(1380, 1500, "late", "CRJ200", "ron", None, None)
        early = GateClaim(30, 60, "early", "CRJ200", "turn", None, None)
        separate = GateClaim(120, 180, "separate", "CRJ200", "turn", None, None)
        self.assertTrue(overlaps(late, early))
        self.assertFalse(overlaps(late, separate))

    def test_fixed_inventory_uses_elapsed_hold_across_route_day_cut(self) -> None:
        legs = [
            {
                "line": "AA",
                "day": 1,
                "route": 101,
                "fleet": "CRJ200",
                "origin": "BBB",
                "destination": "AAA",
                "departureMinute": 60,
                "arrivalMinute": 272,
            },
            {
                "line": "AA",
                "day": 2,
                "route": 102,
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "CCC",
                "departureMinute": 315,
                "arrivalMinute": 400,
            },
        ]

        legacy = build_claims(legs, "AAA")
        fixed_inventory = build_claims(
            legs,
            "AAA",
            cyclic_successor_holds=True,
        )

        self.assertEqual((legacy[0].end, legacy[0].kind), (1755, "ron"))
        self.assertEqual(
            (fixed_inventory[0].end, fixed_inventory[0].kind),
            (315, "turn"),
        )

    def test_fixed_inventory_keeps_red_eye_route_sequence_across_midnight(
        self,
    ) -> None:
        legs = [
            {
                "line": "AA",
                "day": 1,
                "route": 101,
                "sequenceWithinRoute": 1,
                "fleet": "CRJ200",
                "origin": "BBB",
                "destination": "AAA",
                "departureMinute": 1320,
                "arrivalMinute": 1380,
            },
            {
                "line": "AA",
                "day": 1,
                "route": 101,
                "sequenceWithinRoute": 2,
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "CCC",
                "departureMinute": 30,
                "arrivalMinute": 90,
            },
        ]

        claims = build_claims(
            legs,
            "AAA",
            cyclic_successor_holds=True,
        )

        self.assertEqual(len(claims), 1)
        self.assertEqual(
            claims[0],
            GateClaim(
                1380,
                1470,
                "101",
                "CRJ200",
                "turn",
                "BBB",
                "CCC",
            ),
        )

    def test_gate_rescue_does_not_reuse_reserved_touch_slot(self) -> None:
        claims = [
            GateClaim(1050, 1170, "0", "CRJ200", "turn", "A", "B"),
            GateClaim(180, 780, "1", "CRJ200", "turn", "A", "B"),
            GateClaim(180, 270, "2", "CRJ200", "turn", "A", "B"),
            GateClaim(210, 255, "3", "CRJ200", "turn", "A", "B"),
            GateClaim(90, 210, "4", "CRJ200", "turn", "A", "B"),
        ]
        assignments = assign_gates(claims, 1)
        by_slot: dict[int, list[GateClaim]] = {}
        for claim, slot in assignments:
            by_slot.setdefault(slot, []).append(claim)
        conflicts = [
            (first.label, second.label)
            for slot_claims in by_slot.values()
            for index, first in enumerate(slot_claims)
            for second in slot_claims[index + 1 :]
            if overlaps(first, second)
        ]
        self.assertEqual(conflicts, [])

    def test_bounded_assignment_uses_a_stand_only_for_a_long_hold_middle(self) -> None:
        overnight = GateClaim(1200, 1800, "ron", "CRJ200", "ron", "A", "B")
        passenger_turn = GateClaim(1300, 1360, "turn", "CRJ200", "turn", "C", "D")

        assignments, stand_middles = assign_gates(
            [overnight, passenger_turn],
            1,
            n_stands=1,
            return_provenance=True,
        )

        self.assertEqual(len(stand_middles), 1)
        self.assertTrue(
            all(
                slot == 1
                for claim, slot in assignments
                if claim not in stand_middles
            )
        )
        self.assertEqual(
            {slot for claim, slot in assignments if claim in stand_middles},
            {2},
        )

    def test_bounded_assignment_never_synthesizes_an_extra_stand(self) -> None:
        claims = [
            GateClaim(1200, 1800, str(index), "CRJ200", "ron", "A", "B")
            for index in range(3)
        ]

        with self.assertRaises(GateCapacityError) as raised:
            assign_gates(claims, 1, n_stands=1)

        self.assertGreater(raised.exception.required_stands, 1)
        self.assertEqual(raised.exception.configured_stands, 1)

    def test_preview_marks_excess_inventory_as_unassigned(self) -> None:
        claims = [
            GateClaim(1200, 1800, str(index), "CRJ200", "ron", "A", "B")
            for index in range(3)
        ]

        assignments, stand_middles = assign_gates(
            claims,
            1,
            n_stands=1,
            return_provenance=True,
            allow_infeasible_preview=True,
        )
        serialized = serialize_assignments(
            assignments,
            1,
            n_stands=1,
            stand_middles=stand_middles,
        )

        self.assertTrue(any(row["rowType"] == "overflow" for row in serialized))
        self.assertFalse(
            any(row["rowType"] == "stand" and row["row"] > 1 for row in serialized)
        )

    def test_ron_claims_stay_at_gates_when_all_continuous_holds_fit(self) -> None:
        claims = [
            GateClaim(1200, 1800, str(index), "CRJ200", "ron", "A", "B")
            for index in range(4)
        ]

        assignments, stand_middles = assign_gates(
            claims,
            4,
            n_stands=4,
            return_provenance=True,
        )

        self.assertFalse(stand_middles)
        self.assertTrue(all(slot <= 4 for _, slot in assignments))

    def test_bounded_coloring_proves_capacity_after_greedy_overstates_it(self) -> None:
        claims = [
            GateClaim(start, end, str(index), "CRJ200", "turn", "A", "B")
            for index, (start, end) in enumerate(
                (
                    (600, 1020),
                    (120, 420),
                    (840, 1050),
                    (840, 1290),
                    (180, 540),
                    (360, 810),
                    (1200, 1650),
                )
            )
        ]

        self.assertEqual(max(_greedy_coloring(claims)), 4)
        coloring = _bounded_coloring(claims, 3)
        self.assertIsNotNone(coloring)
        assert coloring is not None
        self.assertEqual(max(coloring), 3)

    def test_operating_validator_exposes_known_baseline_findings(self) -> None:
        report = validate_operating_rules(self.canonical)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["summary"],
            {
                "checks": 24,
                "passed": 10,
                "failed": 7,
                "warnings": 4,
                "notEvaluated": 3,
                "overridden": 0,
                "effectiveErrorFindings": 55,
                "effectiveWarningFindings": 156,
            },
        )
        checks = {check["id"]: check for check in report["checks"]}
        self.assertEqual(checks["fleet_capacity"]["status"], "pass")
        self.assertEqual(checks["departure_windows"]["status"], "pass")
        self.assertEqual(checks["point_to_point_share"]["status"], "pass")
        self.assertEqual(checks["minimum_turn_time"]["status"], "fail")
        self.assertEqual(
            checks["section_26_service_gap_policy_consistency"]["status"],
            "warning",
        )
        self.assertEqual(checks["departure_windows"]["hardStop"], True)
        self.assertEqual(
            checks["section_26_city_departure_gap"]["status"], "warning"
        )
        self.assertEqual(checks["runway_screening"]["status"], "not_evaluated")
        self.assertEqual(checks["hub_bank_alignment"]["status"], "not_evaluated")
        self.assertEqual(len(checks["market_frequency_ceiling"]["findings"]), 3)
        self.assertEqual(len(checks["passenger_touch_on_stand"]["findings"]), 35)

    def test_fixed_inventory_mode_turns_synthesized_positions_into_hard_stops(self) -> None:
        candidate = copy.deepcopy(self.canonical)
        candidate["gatePlan"]["fixedPhysicalInventory"] = True

        report = validate_operating_rules(candidate)
        checks = {check["id"]: check for check in report["checks"]}

        self.assertEqual(checks["fixed_physical_inventory"]["status"], "fail")
        self.assertTrue(checks["fixed_physical_inventory"]["hardStop"])
        self.assertTrue(checks["passenger_touch_on_stand"]["hardStop"])
        self.assertTrue(checks["stand_capacity"]["hardStop"])

    def test_fleet_counts_are_schedule_specific(self) -> None:
        candidate = copy.deepcopy(self.canonical)
        self.assertNotIn("fleetCapacity", candidate["operatingPolicy"])
        candidate["schedule"]["fleetCounts"]["MAX9"] = 34
        report = validate_operating_rules(candidate)
        check = next(item for item in report["checks"] if item["id"] == "fleet_capacity")
        self.assertEqual(check["status"], "fail")
        self.assertEqual(check["findings"][0]["evidence"]["capacity"], 34)

    def test_curfew_violation_is_a_hard_stop(self) -> None:
        candidate = copy.deepcopy(self.canonical)
        candidate["legs"][0]["departureMinute"] = 200
        candidate["legs"][0]["arrivalMinute"] = 260
        first = validate_operating_rules(candidate)
        first_check = next(
            item for item in first["checks"] if item["id"] == "departure_windows"
        )
        candidate["operatingPolicy"]["overrides"] = [
            {
                "checkId": "departure_windows",
                "findingId": first_check["findings"][0]["id"],
                "reason": "Hard stops must ignore this attempted override",
            }
        ]
        report = validate_operating_rules(candidate)
        check = next(item for item in report["checks"] if item["id"] == "departure_windows")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(check["hardStop"])
        self.assertNotIn("override", check["findings"][0])

    def test_hub_bank_validator_requires_definition_and_touch_assignments(self) -> None:
        candidate = copy.deepcopy(self.canonical)
        candidate["hubBanks"] = []
        candidate["bankAssignments"] = []
        report = validate_operating_rules(candidate)
        check = next(item for item in report["checks"] if item["id"] == "hub_bank_alignment")
        self.assertEqual(check["status"], "fail")
        self.assertGreater(len(check["findings"]), 5)

    def test_operating_override_requires_exact_finding_id(self) -> None:
        broken = copy.deepcopy(self.canonical)
        first = validate_operating_rules(broken)
        check = next(item for item in first["checks"] if item["id"] == "minimum_turn_time")
        finding = check["findings"][0]
        broken["operatingPolicy"]["overrides"] = [
            {
                "checkId": "minimum_turn_time",
                "findingId": finding["id"],
                "reason": "Regression-test approval only",
                "approvedBy": "test",
            }
        ]
        second = validate_operating_rules(broken)
        updated = next(item for item in second["checks"] if item["id"] == "minimum_turn_time")
        self.assertIn("override", updated["findings"][0])
        self.assertEqual(updated["metrics"]["overriddenFindingCount"], 1)

    def test_baseline_validator_passes(self) -> None:
        report = validate_schedule(self.canonical)
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(report["summary"]["failed"], 0)

    def test_validator_rejects_duplicate_flight_numbers(self) -> None:
        broken = copy.deepcopy(self.canonical)
        broken["legs"][1]["flight"] = broken["legs"][0]["flight"]
        report = validate_schedule(broken)
        check = next(item for item in report["checks"] if item["id"] == "unique_flight_numbers")
        self.assertEqual(check["status"], "fail")

    def test_validator_rejects_route_discontinuity(self) -> None:
        broken = copy.deepcopy(self.canonical)
        first_route = broken["legs"][0]["route"]
        route_legs = [leg for leg in broken["legs"] if leg["route"] == first_route]
        route_legs[1]["origin"] = "XXX"
        report = validate_schedule(broken)
        check = next(item for item in report["checks"] if item["id"] == "routing_continuity")
        self.assertEqual(check["status"], "fail")

    def test_import_is_deterministic(self) -> None:
        second = import_canonical_schedule(
            workbook_path=WORKBOOK,
            city_information_path=CITY_INFORMATION,
            schedule=SCHEDULE,
            connection_window=CONNECTION_WINDOW,
            gate_plan=GATE_PLAN,
            gate_baseline_path=EXPECTED_GATE,
            operating_policy_path=OPERATING_POLICY,
        )
        self.assertEqual(
            json.dumps(self.canonical, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_baseline_command_writes_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            config = {
                "schedule": SCHEDULE,
                "connectionWindowMinutes": CONNECTION_WINDOW,
                "gatePlan": GATE_PLAN,
                "inputs": {
                    "workbook": str(WORKBOOK),
                    "cityInformation": str(CITY_INFORMATION),
                    "expectedTimetable": str(EXPECTED_TIMETABLE),
                    "expectedGate": str(EXPECTED_GATE),
                    "operatingPolicy": str(OPERATING_POLICY),
                    "demandData": {
                        "version": "bts-db1c-6mo-jul2025-apr2026-v3",
                        "manifest": "config/demand_data/bts_db1c_6mo_v3.json",
                    },
                },
                "outputs": {"directory": str(temp_root / "out")},
            }
            config_path = temp_root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            result = build_baseline(config_path, REPO_ROOT)
            self.assertTrue(result["timetableParity"])
            self.assertTrue(result["timetableByteParity"])
            self.assertTrue(result["gateParity"])
            self.assertTrue(result["gateByteParity"])
            self.assertEqual(result["validation"]["status"], "pass")
            self.assertTrue(result["canonicalPath"].exists())
            self.assertTrue(result["timetablePath"].exists())
            self.assertTrue(result["gatePath"].exists())
            self.assertTrue(result["validationPath"].exists())
            self.assertTrue(result["operatingValidationPath"].exists())
            self.assertTrue(result["planningPath"].exists())
            self.assertTrue(result["planningValidationPath"].exists())
            self.assertTrue(result["demandPlanPath"].exists())
            self.assertTrue(result["frequencyFleetPlanPath"].exists())
            self.assertTrue(result["hubBankPlanPath"].exists())
            self.assertTrue(result["aircraftRoutePlanPath"].exists())
            self.assertTrue(result["routingRepairPlanPath"].exists())
            self.assertTrue(result["bankMaterializationDiagnosticPath"].exists())
            self.assertTrue(result["exactMaterializationPlanPath"].exists())
            self.assertEqual(result["planningValidation"]["status"], "pass")
            self.assertEqual(result["demandPlan"]["status"], "pass")
            self.assertEqual(result["demandPlan"]["assignmentParity"]["matched"], 100)
            self.assertEqual(result["frequencyFleetPlan"]["status"], "pass")
            self.assertEqual(
                result["frequencyFleetPlan"]["summary"]["plannedLegs"], 1430
            )
            self.assertEqual(result["hubBankPlan"]["status"], "pass")
            self.assertEqual(result["hubBankPlan"]["summary"]["placedLegs"], 1190)
            self.assertEqual(
                result["aircraftRoutePlan"]["summary"]["routedLegs"], 1430
            )
            self.assertEqual(
                result["aircraftRoutePlan"]["summary"]["curfewViolations"], 0
            )
            self.assertEqual(result["routingRepairPlan"]["status"], "pass")
            self.assertEqual(
                result["routingRepairPlan"]["summary"]["requiredAircraft"], 209
            )
            self.assertEqual(
                result["bankMaterializationDiagnostic"]["status"],
                "pending_nonhub_integration",
            )
            self.assertEqual(
                result["bankMaterializationDiagnostic"]["fleetPlan"]["CRJ200"][
                    "bankAndRonMinimumAircraft"
                ],
                67,
            )
            self.assertEqual(result["exactMaterializationPlan"]["status"], "pass")
            self.assertEqual(
                result["exactMaterializationPlan"]["summary"]["requiredAircraft"],
                208,
            )
            self.assertEqual(
                result["exactMaterializationPlan"]["summary"]["nonHubIntegratedLegs"],
                240,
            )
            self.assertEqual(
                result["timetablePath"].read_bytes(),
                EXPECTED_TIMETABLE.read_bytes(),
            )
            self.assertEqual(
                result["gatePath"].read_bytes(),
                EXPECTED_GATE.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
