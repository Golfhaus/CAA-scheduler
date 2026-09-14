from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.instructions import (
    build_instruction_catalog,
    instruction_id,
    instruction_references,
)


class InstructionCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = build_instruction_catalog(
            REPO_ROOT / "instructions" / "CAA_Build_Instructions_TEMPLATE_v2_0.md",
            [
                REPO_ROOT
                / "instructions"
                / "additions"
                / "BUILD_INSTRUCTIONS_ADDITION.md"
            ],
            REPO_ROOT,
            "2.0 with turn-on-stand hard-stop addition",
        )

    def test_catalog_extracts_sections_lessons_checks_and_additions(self) -> None:
        entries = {entry["id"]: entry for entry in self.catalog["entries"]}
        self.assertIn("section-1-8", entries)
        self.assertIn("lesson-31", entries)
        self.assertIn("section-2-6-check-a", entries)
        self.assertIn("section-2-6-check-b", entries)
        self.assertIn("section-1-7-hard-stop-addition", entries)
        self.assertIn("full window", entries["lesson-32"]["text"])
        self.assertIn("city-level dead-zone", entries["section-2-6-check-b"]["text"])

    def test_every_validation_reference_resolves_to_instruction_text(self) -> None:
        report = json.loads(
            (
                REPO_ROOT
                / "data"
                / "schedules"
                / "schedule_6_v2_2_5"
                / "operating_validation_report.json"
            ).read_text()
        )
        entries = {entry["id"]: entry for entry in self.catalog["entries"]}
        missing = []
        for check in report["checks"]:
            for reference in instruction_references(check["section"]):
                if instruction_id(reference) not in entries:
                    missing.append(reference)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
