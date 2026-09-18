from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.cli import main
from caa_scheduler.exact_materialization import (
    ExactGlobalRepairIncomplete,
    ExactSeedStageComplete,
)


class SchedulerCliTests(unittest.TestCase):
    @patch("caa_scheduler.cli.write_json")
    @patch("caa_scheduler.cli.build_frequency_fleet_plan_from_manifest")
    @patch("caa_scheduler.cli.read_json")
    def test_frequency_build_does_not_receive_exact_seed_options(
        self,
        read_json_mock,
        build_mock,
        _write_json_mock,
    ) -> None:
        canonical = {"schedule": {"id": "test"}}
        demand = {"status": "pass"}
        read_json_mock.side_effect = [canonical, demand]
        build_mock.return_value = {
            "status": "pass",
            "summary": {"plannedLegs": 2, "candidateMarkets": 1},
        }

        result = main(
            [
                "build-frequency-plan",
                "canonical.json",
                "demand.json",
                "manifest.json",
                "frequency.json",
                "--repo-root",
                ".",
            ]
        )

        self.assertEqual(result, 0)
        build_mock.assert_called_once_with(
            canonical,
            demand,
            Path("manifest.json"),
            Path.cwd().resolve(),
        )

    @patch("caa_scheduler.cli.write_json")
    @patch("caa_scheduler.cli.build_exact_materialization_plan_from_manifest")
    @patch("caa_scheduler.cli.read_json")
    def test_exact_seed_step_exits_cleanly_after_checkpoint(
        self,
        read_json_mock,
        build_mock,
        write_json_mock,
    ) -> None:
        artifacts = [{"id": name} for name in ("canonical", "frequency", "bank", "repair")]
        read_json_mock.side_effect = artifacts
        build_mock.side_effect = ExactSeedStageComplete(["CRJ200"])

        result = main(
            [
                "build-exact-materialization",
                "canonical.json",
                "frequency.json",
                "bank.json",
                "repair.json",
                "manifest.json",
                "exact.json",
                "--repo-root",
                ".",
                "--seed-checkpoint",
                "seed.json",
                "--seed-fleets-per-run",
                "1",
            ]
        )

        self.assertEqual(result, 0)
        build_mock.assert_called_once_with(
            *artifacts,
            Path("manifest.json"),
            Path.cwd().resolve(),
            Path("seed.json"),
            1,
        )
        write_json_mock.assert_not_called()

    @patch("caa_scheduler.cli.write_json")
    @patch("caa_scheduler.cli.build_exact_materialization_plan_from_manifest")
    @patch("caa_scheduler.cli.read_json")
    def test_incomplete_global_repair_exits_after_saving_incumbent(
        self,
        read_json_mock,
        build_mock,
        write_json_mock,
    ) -> None:
        read_json_mock.side_effect = [
            {"id": name}
            for name in ("canonical", "frequency", "bank", "repair")
        ]
        build_mock.side_effect = ExactGlobalRepairIncomplete(
            {"JAX-B14:arrival": 4.0},
            "Time limit reached",
        )

        result = main(
            [
                "build-exact-materialization",
                "canonical.json",
                "frequency.json",
                "bank.json",
                "repair.json",
                "manifest.json",
                "exact.json",
                "--seed-checkpoint",
                "seed.json",
            ]
        )

        self.assertEqual(result, 1)
        write_json_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
