from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import read_json
from caa_scheduler.optimization_review import build_optimization_review


class OptimizationReviewTests(unittest.TestCase):
    def test_review_package_is_authoritative_and_audits_every_pair(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            output = Path(directory) / "review"
            report = build_optimization_review(
                REPO_ROOT
                / "config"
                / "optimizations"
                / "schedule_7_v1_1_0_review.json",
                REPO_ROOT,
                output_directory=output,
            )
            self.assertEqual(report["status"], "candidate_review_required")
            self.assertEqual(report["summary"]["legs"], 948)
            self.assertEqual(report["summary"]["connectedDirectionalPairs"], 34)

            canonical = read_json(output / "canonical_schedule.json")
            self.assertEqual(canonical["schedule"]["id"], "schedule_7_v1_1_0_review")
            self.assertEqual(
                len(canonical["provenance"]["optimizationReview"]["overlays"]),
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
                "optimization_review_report.json",
            }
            self.assertEqual(
                {path.name for path in output.iterdir() if path.is_file()},
                expected_files,
            )


if __name__ == "__main__":
    unittest.main()
