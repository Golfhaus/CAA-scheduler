from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


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
            "MAX9": 36,
            "CRJ900": 46,
            "CRJ700": 66,
            "CRJ200": 81,
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
            "demandData": {"version": "test-demand-snapshot"},
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

    def test_build_writes_candidate_package_after_hard_stops_pass(self) -> None:
        config = _config(self.baseline)
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
            self.assertEqual(report["status"], "candidate_review_required")
            for filename in (
                "build_config.json",
                "build_report.json",
                "canonical_schedule.json",
                "validation_report.json",
                "operating_validation_report.json",
                "timetable.json",
                "gates.json",
            ):
                self.assertTrue((output / filename).is_file(), filename)

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
            first = build_candidate(
                config_path,
                REPO_ROOT,
                baseline_path=baseline_path,
                output_directory=output,
            )
            self.assertEqual(first["status"], "candidate_review_required")
            self.assertTrue((output / "canonical_schedule.json").exists())

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


if __name__ == "__main__":
    unittest.main()
