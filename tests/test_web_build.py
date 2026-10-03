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
from latest_schedule import MANIFEST, ENTRY, SCHEDULE_ID


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
        self.assertIn(
            'src="app.mjs?v=console-ui-20261003-2"',
            html,
        )
        self.assertIn(
            'href="styles.css?v=console-ui-20261003-2"',
            html,
        )
        self.assertNotIn('`${auditHub} target cities`', script)
        self.assertNotIn("minute ${auditHub} window", script)
        tabs = re.findall(r'data-tab="([^"]+)"', html)
        self.assertEqual(
            tabs,
            [
                "overview",
                "planning",
                "routings",
                "validation",
                "timetable",
                "sked-stats",
                "gates",
                "instructions",
                "setup",
            ],
        )
        self.assertIn('id="routing-reset"', html)
        self.assertIn('$("#routing-reset").addEventListener', script)
        self.assertIn('id="deps-hub-rows"', html)
        self.assertIn('data-deps-origin', script)
        self.assertIn('data-stats-tab="deps-hubs"', html)
        self.assertIn('data-stats-tab="extension-opps"', html)
        self.assertIn('data-stats-tab="hub-bank-breakdown"', html)
        self.assertIn('id="extension-originator-rows"', html)
        self.assertIn('id="extension-terminator-rows"', html)
        self.assertIn('id="extension-hold-rows"', html)
        self.assertIn("data-claim-group", script)
        self.assertIn('related.classList.toggle(', script)
        self.assertIn(".claim-bar.is-related", (REPO_ROOT / "web" / "styles.css").read_text())

    def test_build_copies_console_and_pinned_schedule_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            result = build_web_console(
                REPO_ROOT / "web" / "schedules.json", REPO_ROOT, output
            )
            self.assertEqual(result["scheduleCount"], len(MANIFEST["schedules"]))
            self.assertEqual(result["dataFileCount"], 115)
            self.assertGreater(result["instructionEntryCount"], 40)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "favicon.svg").is_file())
            self.assertTrue((output / "coastal-american-logo.png").is_file())
            self.assertTrue((output / "build-config.mjs").is_file())
            self.assertEqual((output / "hub-bank-breakdown.mjs").read_text(), (REPO_ROOT / "web" / "hub-bank-breakdown.mjs").read_text())
            manifest = json.loads((output / "schedules.json").read_text())
            self.assertEqual(
                manifest["defaultScheduleId"], SCHEDULE_ID
            )
            self.assertEqual(
                [schedule["id"] for schedule in manifest["schedules"]],
                [item["id"] for item in MANIFEST["schedules"]],
            )
            self.assertTrue((output / manifest["buildSetup"]["schema"]).is_file())
            files = ENTRY["files"]
            for relative_path in files.values():
                self.assertTrue((output / relative_path).is_file())
            self.assertNotIn("frequencyFleetPlan", files)
            self.assertNotIn("exactMaterializationPlan", files)
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



if __name__ == "__main__":
    unittest.main()
