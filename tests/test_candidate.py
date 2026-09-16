from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.build_config import validate_build_config
from caa_scheduler.candidate import build_candidate, compile_candidate


CANONICAL_PATH = (
    REPO_ROOT
    / "data"
    / "schedules"
    / "schedule_6_v2_2_5"
    / "canonical_schedule.json"
)


def _config(baseline: dict) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "buildId": "schedule_7_v0_1_0",
        "schedule": {
            "number": 7,
            "version": "0.1.0",
            "label": "Schedule 7 candidate",
            "mode": "mainline",
            "status": "draft",
        },
        "startingPoint": {
            "kind": "previous_schedule",
            "scheduleId": baseline["schedule"]["id"],
        },
        "fleetCounts": {
            "MAX9": 35,
            "CRJ900": 45,
            "CRJ700": 65,
            "CRJ200": 80,
        },
        "connectionWindowMinutes": {"minimum": 30, "maximum": 240},
        "inputs": {
            "instructions": {
                "version": "2.0 with turn-on-stand hard-stop addition",
                "source": "instructions/CAA_Build_Instructions_TEMPLATE_v2_0.md",
            },
            "cityInformation": copy.deepcopy(
                baseline["provenance"]["cityInformation"]
            ),
            "operatingPolicy": copy.deepcopy(
                baseline["provenance"]["operatingPolicy"]
            ),
            "demandData": {"version": "bts-db1c-6mo-jul2025-apr2026-v3"},
        },
        "networkChanges": [],
        "notes": "Regression candidate",
    }


class CandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(CANONICAL_PATH.read_text())

    def test_python_preflight_accepts_explicit_schedule_inputs(self) -> None:
        report = validate_build_config(_config(self.baseline), self.baseline)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["failed"], 0)

    def test_accepted_schedule_seven_configuration_is_pinned(self) -> None:
        config = json.loads(
            (
                REPO_ROOT
                / "config"
                / "candidates"
                / "schedule_7_v0_1_0.json"
            ).read_text()
        )
        report = validate_build_config(config, self.baseline)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            config["fleetCounts"],
            {"MAX9": 35, "CRJ900": 45, "CRJ700": 65, "CRJ200": 80},
        )

    def test_candidate_uses_only_configuration_fleet_counts(self) -> None:
        config = _config(self.baseline)
        candidate, report = compile_candidate(config, self.baseline)
        self.assertIsNotNone(candidate)
        self.assertEqual(report["status"], "candidate_review_required")
        self.assertEqual(candidate["schedule"]["fleetCounts"], config["fleetCounts"])
        self.assertEqual(candidate["schedule"]["id"], config["buildId"])
        self.assertEqual(self.baseline["schedule"]["fleetCounts"]["MAX9"], 35)
        departure_check = next(
            check
            for check in report["operatingValidation"]["checks"]
            if check["id"] == "departure_windows"
        )
        self.assertTrue(departure_check["hardStop"])
        self.assertEqual(departure_check["status"], "pass")

    def test_build_retains_exact_diagnostics_before_canonical_ids(self) -> None:
        config = _config(self.baseline)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "build_config.json"
            output = root / "candidate"
            config_path.write_text(json.dumps(config))
            with patch(
                "caa_scheduler.candidate.build_exact_materialization_plan_from_manifest",
                side_effect=ValueError(
                    "Exact CRJ200 materialization failed: time limit reached"
                ),
            ):
                report = build_candidate(
                    config_path,
                    REPO_ROOT,
                    baseline_path=CANONICAL_PATH,
                    output_directory=output,
                )
            self.assertEqual(report["status"], "blocked_planning_input")
            for filename in (
                "build_config.json",
                "build_report.json",
                "validation_report.json",
                "operating_validation_report.json",
                "planning_snapshot.json",
                "planning_validation_report.json",
                "demand_plan.json",
                "frequency_fleet_plan.json",
                "hub_bank_plan.json",
                "aircraft_route_plan.json",
                "routing_repair_plan.json",
                "bank_materialization_diagnostic.json",
                "exact_materialization_plan.json",
            ):
                self.assertTrue((output / filename).is_file(), filename)
            planning = json.loads((output / "planning_snapshot.json").read_text())
            self.assertEqual(
                planning["demandDataVersion"],
                "bts-db1c-6mo-jul2025-apr2026-v3",
            )
            self.assertEqual(report["planningValidation"]["status"], "pass")
            self.assertEqual(report["demandPlan"]["assignmentParity"]["matched"], 100)
            self.assertEqual(report["frequencyFleetPlan"]["status"], "pass")
            self.assertEqual(
                report["frequencyFleetPlan"]["fleetPlan"]["MAX9"]["aircraftCount"],
                config["fleetCounts"]["MAX9"],
            )
            self.assertEqual(report["hubBankPlan"]["status"], "pass")
            self.assertEqual(report["hubBankPlan"]["summary"]["curfewViolations"], 0)
            route_plan = report["aircraftRoutePlan"]
            self.assertEqual(
                route_plan["summary"]["routedLegs"],
                report["frequencyFleetPlan"]["summary"]["plannedLegs"],
            )
            self.assertEqual(route_plan["summary"]["curfewViolations"], 0)
            self.assertEqual(
                route_plan["fleetPlan"]["MAX9"]["configuredAircraft"],
                config["fleetCounts"]["MAX9"],
            )
            repair = report["routingRepairPlan"]
            self.assertEqual(repair["status"], "pass")
            self.assertEqual(repair["summary"]["aircraftShortfall"], 0)
            self.assertEqual(repair["summary"]["curfewViolations"], 0)
            self.assertEqual(repair["materializationStatus"], "pending_bank_alignment")
            materialization = report["bankMaterializationDiagnostic"]
            self.assertEqual(
                materialization["status"], "pending_nonhub_integration"
            )
            self.assertEqual(
                materialization["fleetPlan"]["CRJ200"]["shortfall"], 0
            )
            exact = report["exactMaterializationPlan"]
            self.assertEqual(exact["status"], "fail")
            self.assertEqual(
                exact["summary"]["plannedLegs"],
                report["frequencyFleetPlan"]["summary"]["plannedLegs"],
            )
            self.assertEqual(exact["materializationStatus"], "blocked")
            self.assertEqual(
                exact["nextStep"]["action"], "retry_exact_materialization"
            )
            self.assertIn("time limit", exact["diagnostics"]["solverFailure"])
            self.assertFalse((output / "canonical_schedule.json").exists())
            self.assertFalse((output / "timetable.json").exists())
            self.assertFalse((output / "gates.json").exists())

    def test_passing_exact_plan_advances_to_reviewable_canonical_outputs(self) -> None:
        config = _config(self.baseline)
        exact = json.loads(
            (
                REPO_ROOT
                / "data"
                / "schedules"
                / "schedule_6_v2_2_5"
                / "exact_materialization_plan.json"
            ).read_text()
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "build_config.json"
            output = root / "candidate"
            config_path.write_text(json.dumps(config))
            with patch(
                "caa_scheduler.candidate.build_exact_materialization_plan_from_manifest",
                return_value=exact,
            ):
                report = build_candidate(
                    config_path,
                    REPO_ROOT,
                    baseline_path=CANONICAL_PATH,
                    output_directory=output,
                )
            self.assertEqual(report["status"], "candidate_review_required")
            self.assertFalse(report["publicationReady"])
            self.assertEqual(report["canonicalization"]["status"], "pass")
            self.assertEqual(
                report["canonicalization"]["summary"]["routes"], 208
            )
            self.assertEqual(report["structuralValidation"]["status"], "pass")
            self.assertTrue((output / "canonical_schedule.json").is_file())
            self.assertTrue((output / "canonicalization_report.json").is_file())
            self.assertTrue((output / "timetable.json").is_file())
            self.assertTrue((output / "gates.json").is_file())
            canonical = json.loads((output / "canonical_schedule.json").read_text())
            self.assertNotIn("workbook", canonical["provenance"])
            self.assertEqual(
                canonical["provenance"]["construction"]["sourceScheduleId"],
                self.baseline["schedule"]["id"],
            )
            checks = {
                check["id"]: check
                for check in report["operatingValidation"]["checks"]
            }
            self.assertEqual(checks["departure_windows"]["status"], "pass")
            self.assertEqual(checks["hub_bank_alignment"]["status"], "pass")
            self.assertEqual(
                checks["section_26_pairing_spacing"]["status"], "fail"
            )

    def test_missing_demand_pin_blocks_before_compilation(self) -> None:
        config = _config(self.baseline)
        config["inputs"]["demandData"]["version"] = ""
        candidate, report = compile_candidate(config, self.baseline)
        self.assertIsNone(candidate)
        self.assertEqual(report["status"], "blocked_preflight")

    def test_blank_start_and_airport_addition_wait_for_planning_stage(self) -> None:
        blank = _config(self.baseline)
        blank["startingPoint"] = {"kind": "blank", "scheduleId": None}
        candidate, report = compile_candidate(blank, self.baseline)
        self.assertIsNone(candidate)
        self.assertEqual(report["status"], "blocked_planning_input")

        addition = _config(self.baseline)
        addition["networkChanges"].append(
            {
                "airport": "ZZZ",
                "action": "add",
                "targetStatus": "destination",
                "notes": "Synthetic test airport",
            }
        )
        candidate, report = compile_candidate(addition, self.baseline)
        self.assertIsNone(candidate)
        self.assertEqual(report["status"], "blocked_planning_input")

    def test_curfew_failure_suppresses_publishable_candidate_outputs(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        config = _config(self.baseline)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / "baseline.json"
            config_path = root / "build_config.json"
            output = root / "candidate"
            baseline_path.write_text(json.dumps(self.baseline))
            config_path.write_text(json.dumps(config))
            output.mkdir()
            (output / "canonical_schedule.json").write_text("stale")
            (output / "timetable.json").write_text("stale")
            (output / "gates.json").write_text("stale")

            leg = baseline["legs"][0]
            leg["departure"] = "02:00"
            leg["arrival"] = "03:00"
            leg["departureMinute"] = 120
            leg["arrivalMinute"] = 180
            config = _config(baseline)
            baseline_path.write_text(json.dumps(baseline))
            config_path.write_text(json.dumps(config))
            report = build_candidate(
                config_path,
                REPO_ROOT,
                baseline_path=baseline_path,
                output_directory=output,
            )
            self.assertEqual(report["status"], "blocked_hard_stop")
            self.assertFalse((output / "canonical_schedule.json").exists())
            self.assertFalse((output / "timetable.json").exists())
            self.assertTrue((output / "operating_validation_report.json").is_file())
            self.assertTrue((output / "planning_snapshot.json").is_file())
            self.assertTrue((output / "demand_plan.json").is_file())
            self.assertTrue((output / "frequency_fleet_plan.json").is_file())
            self.assertTrue((output / "hub_bank_plan.json").is_file())
            self.assertTrue((output / "aircraft_route_plan.json").is_file())
            self.assertTrue((output / "routing_repair_plan.json").is_file())
            self.assertFalse((output / "exact_materialization_plan.json").exists())

    def test_unknown_demand_version_suppresses_candidate_outputs(self) -> None:
        config = _config(self.baseline)
        config["inputs"]["demandData"]["version"] = "unknown-demand-version"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "build_config.json"
            output = root / "candidate"
            config_path.write_text(json.dumps(config))
            report = build_candidate(
                config_path,
                REPO_ROOT,
                baseline_path=CANONICAL_PATH,
                output_directory=output,
            )
            self.assertEqual(report["status"], "blocked_planning_input")
            self.assertFalse((output / "canonical_schedule.json").exists())
            self.assertFalse((output / "timetable.json").exists())
            self.assertFalse((output / "gates.json").exists())


if __name__ == "__main__":
    unittest.main()
