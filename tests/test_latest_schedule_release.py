from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import read_json
from caa_scheduler.optimization_release import build_optimization_release


LATEST_SCHEDULE_ID = "schedule_7_v1_1_5"
LATEST_RELEASE_CONFIG = (
    REPO_ROOT / "config" / "optimizations" / "schedule_7_v1_1_5.json"
)
LATEST_RELEASE_DIRECTORY = REPO_ROOT / "data" / "schedules" / LATEST_SCHEDULE_ID


class LatestScheduleReleaseTests(unittest.TestCase):
    @staticmethod
    def _normalize_interchangeable_gate_rows(gates: dict) -> dict:
        normalized = copy.deepcopy(gates)
        for city in normalized["cities"]:
            for claim in city["claims"]:
                claim.pop("row", None)
                for move in ("moveFrom", "moveTo"):
                    if isinstance(claim.get(move), dict):
                        claim[move].pop("row", None)
            city["claims"].sort(
                key=lambda claim: json.dumps(claim, sort_keys=True)
            )
        return normalized

    def test_latest_release_is_default_and_rebuilds_operationally(self) -> None:
        manifest = read_json(REPO_ROOT / "web" / "schedules.json")
        self.assertEqual(manifest["defaultScheduleId"], LATEST_SCHEDULE_ID)
        self.assertEqual(manifest["schedules"][-1]["id"], LATEST_SCHEDULE_ID)

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            output = Path(directory) / "release"
            report = build_optimization_release(
                LATEST_RELEASE_CONFIG,
                REPO_ROOT,
                output_directory=output,
            )
            self.assertEqual(report["status"], "released")
            self.assertEqual(report["scheduleId"], LATEST_SCHEDULE_ID)
            self.assertEqual(report["summary"]["legs"], 1062)
            self.assertEqual(report["summary"]["effectiveOperatingErrors"], 0)
            self.assertEqual(report["summary"]["hardStopFailures"], 0)

            generated = {path.name for path in output.iterdir() if path.is_file()}
            committed = {
                path.name
                for path in LATEST_RELEASE_DIRECTORY.iterdir()
                if path.is_file()
            }
            self.assertEqual(generated, committed)
            for filename in sorted(generated):
                generated_artifact = read_json(output / filename)
                committed_artifact = read_json(
                    LATEST_RELEASE_DIRECTORY / filename
                )
                if filename == "gates.json":
                    generated_artifact = self._normalize_interchangeable_gate_rows(
                        generated_artifact
                    )
                    committed_artifact = self._normalize_interchangeable_gate_rows(
                        committed_artifact
                    )
                self.assertEqual(
                    generated_artifact,
                    committed_artifact,
                    filename,
                )


if __name__ == "__main__":
    unittest.main()
