from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import read_json
from caa_scheduler.operating_validation import (
    _service_window_gaps,
    validate_operating_rules,
)


class OperatingValidationTests(unittest.TestCase):
    def test_city_departure_gaps_only_compare_flights_in_the_service_day(self) -> None:
        self.assertEqual(
            _service_window_gaps([60, 510, 900, 1400], 270, 1260),
            [
                {"from": 510, "to": 900, "minutes": 390},
            ],
        )

    def test_schedule_seven_gap_findings_exclude_the_overnight_period(self) -> None:
        canonical = read_json(
            REPO_ROOT
            / "data"
            / "schedules"
            / "schedule_7_v1_1_1"
            / "canonical_schedule.json"
        )
        report = validate_operating_rules(canonical)
        checks = {check["id"]: check for check in report["checks"]}
        gap_check = checks["section_26_city_departure_gap"]
        self.assertTrue(gap_check["findings"])
        self.assertTrue(
            all(
                finding["evidence"]["serviceWindowMinutes"]
                == {"start": 270, "end": 1260}
                and not finding["evidence"]["includesOvernightWrap"]
                and all(
                    270 <= gap["from"] < gap["to"] <= 1260
                    for gap in finding["evidence"]["excessiveGaps"]
                )
                for finding in gap_check["findings"]
            )
        )
        self.assertEqual(
            checks["section_26_service_gap_policy_consistency"]["status"],
            "pass",
        )


if __name__ == "__main__":
    unittest.main()
