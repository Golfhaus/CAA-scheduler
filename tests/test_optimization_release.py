from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import read_json
from caa_scheduler.optimization_release import build_optimization_release


class OptimizationReleaseTests(unittest.TestCase):
    def test_release_package_is_authoritative_and_audits_every_pair(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            output = Path(directory) / "release"
            report = build_optimization_release(
                REPO_ROOT
                / "config"
                / "optimizations"
                / "schedule_7_v1_1_0.json",
                REPO_ROOT,
                output_directory=output,
            )
            self.assertEqual(report["status"], "released")
            self.assertEqual(report["summary"]["legs"], 948)
            self.assertEqual(report["summary"]["connectedDirectionalPairs"], 34)

            canonical = read_json(output / "canonical_schedule.json")
            self.assertEqual(canonical["schedule"]["id"], "schedule_7_v1_1_0")
            self.assertEqual(
                len(canonical["provenance"]["optimizationRelease"]["overlays"]),
                2,
            )

            audit = read_json(output / "connection_audit.json")
            self.assertEqual(audit["summary"]["targetCities"], 14)
            self.assertEqual(audit["summary"]["directRoundTripCities"], 14)
            self.assertEqual(audit["summary"]["directionalPairs"], 98)
            self.assertEqual(audit["summary"]["missingDirectionalPairs"], 64)
            self.assertEqual(
                audit["summary"]["bySourceGroup"],
                {
                    "north": {
                        "directionalPairs": 49,
                        "connectedDirectionalPairs": 14,
                        "missingDirectionalPairs": 35,
                    },
                    "south": {
                        "directionalPairs": 49,
                        "connectedDirectionalPairs": 20,
                        "missingDirectionalPairs": 29,
                    },
                },
            )
            self.assertEqual(len(audit["directionalPairs"]), 98)

            expected_files = {
                "canonical_schedule.json",
                "validation_report.json",
                "operating_validation_report.json",
                "planning_snapshot.json",
                "planning_validation_report.json",
                "timetable.json",
                "gates.json",
                "connection_audit.json",
                "release_report.json",
            }
            self.assertEqual(
                {path.name for path in output.iterdir() if path.is_file()},
                expected_files,
            )

    def test_v111_rejoins_avoidable_route_339_tow(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            output = Path(directory) / "release"
            report = build_optimization_release(
                REPO_ROOT
                / "config"
                / "optimizations"
                / "schedule_7_v1_1_1.json",
                REPO_ROOT,
                output_directory=output,
            )
            self.assertEqual(report["summary"]["standClaims"], 33)
            self.assertEqual(report["summary"]["hubStandClaims"], 9)
            self.assertFalse(report["patchScope"]["timetableChanged"])
            self.assertFalse(report["patchScope"]["routingChanged"])

            gates = read_json(output / "gates.json")
            phf = next(city for city in gates["cities"] if city["code"] == "PHF")
            route_339 = [
                claim for claim in phf["claims"] if claim["label"] == "339"
            ]
            self.assertIn(
                (796, 975, "gate"),
                {
                    (claim["start"], claim["end"], claim["rowType"])
                    for claim in route_339
                },
            )
            self.assertFalse(
                any(claim["rowType"] == "stand" for claim in route_339)
            )

            previous = read_json(
                REPO_ROOT
                / "data"
                / "schedules"
                / "schedule_7_v1_1_0"
                / "canonical_schedule.json"
            )
            current = read_json(output / "canonical_schedule.json")
            self.assertEqual(current["legs"], previous["legs"])
            self.assertEqual(
                read_json(output / "timetable.json")["flights"],
                read_json(
                    REPO_ROOT
                    / "data"
                    / "schedules"
                    / "schedule_7_v1_1_0"
                    / "timetable.json"
                )["flights"],
            )


if __name__ == "__main__":
    unittest.main()
