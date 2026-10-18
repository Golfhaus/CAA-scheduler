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
from caa_scheduler.operating_validation import validate_operating_rules
from latest_schedule import SCHEDULE_ID, RELEASE_CONFIG, DIRECTORY


LATEST_SCHEDULE_ID = SCHEDULE_ID
LATEST_RELEASE_CONFIG = RELEASE_CONFIG
LATEST_RELEASE_DIRECTORY = DIRECTORY


class LatestScheduleReleaseTests(unittest.TestCase):
    def test_release_rejects_a_stale_base_pin(self) -> None:
        config = read_json(LATEST_RELEASE_CONFIG)
        config['baseCanonicalSha256'] = '0' * 64
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            config_path = Path(directory) / 'stale.json'
            config_path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'base canonical fingerprint'):
                build_optimization_release(config_path, REPO_ROOT, output_directory=Path(directory) / 'release')
            self.assertFalse((Path(directory) / 'release').exists())

    def test_release_rejects_a_changed_overlay_pin(self) -> None:
        config = read_json(LATEST_RELEASE_CONFIG)
        if not config['overlays']:
            self.skipTest('Release uses a pinned cumulative canonical; base checksum test covers its integrity')
        config['overlaySha256'][config['overlays'][0]] = '0' * 64
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            config_path = Path(directory) / 'stale.json'
            config_path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'overlay fingerprint'):
                build_optimization_release(config_path, REPO_ROOT, output_directory=Path(directory) / 'release')
            self.assertFalse((Path(directory) / 'release').exists())

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
            if LATEST_SCHEDULE_ID == "schedule_7_v1_3_1" and (REPO_ROOT / "config/optimizations/schedule_7_v1_3_2_round_1.json").exists():
                # The corrected validator must reject this known-invalid historical
                # snapshot; reproducing its former false pass would restore the bug.
                current = validate_operating_rules(read_json(LATEST_RELEASE_DIRECTORY / "canonical_schedule.json"))
                check = next(c for c in current["checks"] if c["id"] == "rolling_ron_window")
                self.assertEqual({f["id"] for f in check["findings"]}, {"AC", "AO", "AQ"})
                self.assertEqual(current["summary"]["effectiveErrorFindings"], 3)
                with self.assertRaisesRegex(ValueError, "effectiveOperatingErrors|effective operating errors"):
                    build_optimization_release(LATEST_RELEASE_CONFIG, REPO_ROOT, output_directory=output)
                self.assertFalse(output.exists())
                return
            report = build_optimization_release(
                LATEST_RELEASE_CONFIG,
                REPO_ROOT,
                output_directory=output,
            )
            self.assertEqual(report["status"], "released")
            self.assertEqual(report["scheduleId"], LATEST_SCHEDULE_ID)
            self.assertEqual(report["summary"]["legs"], {"schedule_7_v1_3_1": 1214, "schedule_7_v1_3_2": 1229, "schedule_7_v1_3_3": 1253}[LATEST_SCHEDULE_ID])
            self.assertEqual(report["summary"]["effectiveOperatingErrors"], 0)
            self.assertEqual(report["summary"]["hardStopFailures"], 0)
            self.assertEqual(report["summary"]["overnightTurnFailures"], 0)

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
