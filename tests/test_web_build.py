from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.web_build import build_web_console


class WebBuildTests(unittest.TestCase):
    def test_build_copies_console_and_pinned_schedule_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            result = build_web_console(
                REPO_ROOT / "web" / "schedules.json", REPO_ROOT, output
            )
            self.assertEqual(result["scheduleCount"], 1)
            self.assertEqual(result["dataFileCount"], 5)
            self.assertGreater(result["instructionEntryCount"], 40)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "favicon.svg").is_file())
            self.assertTrue((output / "coastal-american-logo.png").is_file())
            manifest = json.loads((output / "schedules.json").read_text())
            files = manifest["schedules"][0]["files"]
            self.assertTrue((output / files["canonical"]).is_file())
            self.assertTrue((output / files["gates"]).is_file())
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
