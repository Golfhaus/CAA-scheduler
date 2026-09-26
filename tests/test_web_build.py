from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.web_build import build_web_console


class WebBuildTests(unittest.TestCase):
    def test_static_console_defines_every_direct_id_selector(self) -> None:
        html = (REPO_ROOT / "web" / "index.html").read_text()
        script = (REPO_ROOT / "web" / "app.mjs").read_text()
        ids = re.findall(r'\bid="([^"]+)"', html)
        selectors = set(re.findall(r'\$\("#([^"]+)"\)', script))
        self.assertEqual(len(ids), len(set(ids)), "index.html contains duplicate IDs")
        self.assertEqual(selectors - set(ids), set())
        self.assertIn('id="preview-warning"', html)
        self.assertIn("previewNotice", script)

    def test_build_copies_console_and_pinned_schedule_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            result = build_web_console(
                REPO_ROOT / "web" / "schedules.json", REPO_ROOT, output
            )
            self.assertEqual(result["scheduleCount"], 3)
            self.assertEqual(result["dataFileCount"], 41)
            self.assertGreater(result["instructionEntryCount"], 40)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "favicon.svg").is_file())
            self.assertTrue((output / "coastal-american-logo.png").is_file())
            self.assertTrue((output / "build-config.mjs").is_file())
            manifest = json.loads((output / "schedules.json").read_text())
            self.assertEqual(
                manifest["defaultScheduleId"], "schedule_7_v1_1_0_review"
            )
            self.assertEqual(
                [schedule["id"] for schedule in manifest["schedules"]],
                [
                    "schedule_6_v2_2_5",
                    "schedule_7_v1_0_0",
                    "schedule_7_v1_1_0_review",
                ],
            )
            self.assertTrue((output / manifest["buildSetup"]["schema"]).is_file())
            files = manifest["schedules"][0]["files"]
            self.assertTrue((output / files["canonical"]).is_file())
            self.assertTrue((output / files["gates"]).is_file())
            self.assertTrue((output / files["planning"]).is_file())
            self.assertTrue((output / files["demandPlan"]).is_file())
            self.assertTrue((output / files["frequencyFleetPlan"]).is_file())
            self.assertTrue((output / files["hubBankPlan"]).is_file())
            self.assertTrue((output / files["aircraftRoutePlan"]).is_file())
            self.assertTrue((output / files["routingRepairPlan"]).is_file())
            self.assertTrue(
                (output / files["bankMaterializationDiagnostic"]).is_file()
            )
            self.assertTrue(
                (output / files["exactMaterializationPlan"]).is_file()
            )
            demand_setup = manifest["buildSetup"]["demandData"]
            demand_manifest_path = output / demand_setup["manifest"]
            self.assertTrue(demand_manifest_path.is_file())
            demand_manifest = json.loads(demand_manifest_path.read_text())
            self.assertEqual(demand_manifest["id"], demand_setup["version"])
            for source in demand_manifest["sources"].values():
                self.assertTrue((output / source["filename"]).is_file())
            instruction_catalog = json.loads(
                (output / manifest["instructions"]["catalog"]).read_text()
            )
            self.assertTrue(
                any(
                    entry["id"] == "lesson-31"
                    for entry in instruction_catalog["entries"]
                )
            )

    def test_preview_build_supports_overlay_review_without_stale_planning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            result = build_web_console(
                REPO_ROOT / "web" / "schedules.preview.json", REPO_ROOT, output
            )
            self.assertEqual(result["scheduleCount"], 2)
            self.assertEqual(result["dataFileCount"], 27)
            manifest = json.loads((output / "schedules.json").read_text())
            self.assertEqual(
                manifest["defaultScheduleId"], "schedule_7_v1_1_0_review"
            )
            review = next(
                item
                for item in manifest["schedules"]
                if item["id"] == "schedule_7_v1_1_0_review"
            )
            self.assertNotIn("frequencyFleetPlan", review["files"])
            self.assertNotIn("exactMaterializationPlan", review["files"])
            self.assertTrue((output / review["files"]["canonical"]).is_file())
            self.assertTrue(
                (output / review["files"]["connectionAudit"]).is_file()
            )


if __name__ == "__main__":
    unittest.main()
