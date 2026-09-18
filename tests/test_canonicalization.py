from __future__ import annotations

import copy
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.canonicalization import (
    build_canonical_schedule_from_exact_plan,
)
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.validation import validate_schedule


SCHEDULE_DIRECTORY = (
    REPO_ROOT / "data" / "schedules" / "schedule_6_v2_2_5"
)


def _load(filename: str) -> dict:
    return json.loads((SCHEDULE_DIRECTORY / filename).read_text())


class CanonicalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = _load("canonical_schedule.json")
        cls.demand = _load("demand_plan.json")
        cls.frequency = _load("frequency_fleet_plan.json")
        cls.banks = _load("hub_bank_plan.json")
        cls.exact = _load("exact_materialization_plan.json")
        cls.provenance = {
            "sourceKind": "deterministic_planner",
            "sourceScheduleId": cls.seed["schedule"]["id"],
            "buildConfig": {
                "filename": "build_config.json",
                "sha256": "0" * 64,
            },
            "demandData": {
                "id": cls.demand["demandDataVersion"],
                "filename": "config/demand_data/test.json",
                "sha256": "1" * 64,
            },
            "planningRules": {
                "id": cls.exact["planningRulesId"],
                "filename": "config/policies/test.json",
                "sha256": "2" * 64,
            },
            "exactMaterialization": {
                "filename": "exact_materialization_plan.json",
                "sha256": "3" * 64,
            },
        }
        cls.canonical, cls.report = build_canonical_schedule_from_exact_plan(
            cls.seed,
            cls.demand,
            cls.frequency,
            cls.banks,
            cls.exact,
            cls.provenance,
        )

    def test_assigns_every_exact_leg_to_a_line_day_and_route(self) -> None:
        self.assertEqual(
            self.report["summary"],
            {
                "cycles": 23,
                "lines": 23,
                "routes": 208,
                "legs": 1430,
                "pairings": 736,
                "reusedPairings": 634,
                "newPairings": 102,
                "bankAssignments": 1224,
            },
        )
        self.assertEqual(
            {leg["id"] for leg in self.canonical["legs"]},
            {leg["id"] for leg in self.exact["legs"]},
        )
        self.assertEqual(max(self.report["lineDays"].values()), 42)
        self.assertEqual(min(self.report["lineDays"].values()), 1)

    def test_route_sequences_are_contiguous_and_fleet_blocked(self) -> None:
        routes: defaultdict[int, list[dict]] = defaultdict(list)
        for leg in self.canonical["legs"]:
            routes[leg["route"]].append(leg)
            expected_hundred = {
                "CRJ200": 1,
                "CRJ700": 3,
                "CRJ900": 5,
                "MAX9": 7,
            }[leg["fleet"]]
            self.assertEqual(leg["route"] // 100, expected_hundred)
        for legs in routes.values():
            sequences = sorted(leg["sequenceWithinRoute"] for leg in legs)
            self.assertEqual(sequences, list(range(1, len(legs) + 1)))

    def test_line_and_public_numbering_follow_the_standing_conventions(self) -> None:
        max9_lines = {
            leg["line"] for leg in self.canonical["legs"] if leg["fleet"] == "MAX9"
        }
        crj_lines = {
            leg["line"] for leg in self.canonical["legs"] if leg["fleet"] != "MAX9"
        }
        self.assertTrue(all(len(line) == 1 for line in max9_lines))
        self.assertTrue(all(len(line) == 2 for line in crj_lines))
        flights = sorted(leg["flight"] for leg in self.canonical["legs"])
        self.assertEqual(flights, list(range(1001, 2431)))
        pairing_markets: defaultdict[int, set[tuple[str, str]]] = defaultdict(set)
        for leg in self.canonical["legs"]:
            pairing_markets[leg["pairing"]].add(
                (leg["origin"], leg["destination"])
            )
        self.assertTrue(all(len(markets) == 1 for markets in pairing_markets.values()))

    def test_generated_provenance_replaces_legacy_workbook_claim(self) -> None:
        provenance = self.canonical["provenance"]
        self.assertNotIn("workbook", provenance)
        self.assertNotIn("gateTimingBaseline", provenance)
        self.assertEqual(provenance["construction"], self.provenance)
        report = validate_schedule(self.canonical)
        self.assertEqual(report["status"], "pass", report)
        check = next(
            row for row in report["checks"] if row["id"] == "canonical_provenance"
        )
        self.assertEqual(check["status"], "pass")

    def test_full_validation_runs_and_exposes_next_repair_work(self) -> None:
        report = validate_operating_rules(self.canonical)
        checks = {check["id"]: check for check in report["checks"]}
        self.assertEqual(checks["departure_windows"]["status"], "pass")
        self.assertEqual(checks["minimum_turn_time"]["status"], "pass")
        self.assertEqual(checks["hub_bank_alignment"]["status"], "pass")
        self.assertEqual(checks["numbering_conventions"]["status"], "pass")
        self.assertEqual(checks["section_26_pairing_spacing"]["status"], "fail")
        self.assertEqual(checks["passenger_touch_on_stand"]["status"], "fail")
        self.assertEqual(checks["tiered_service_minimums"]["status"], "fail")

    def test_canonicalization_is_deterministic(self) -> None:
        repeated, repeated_report = build_canonical_schedule_from_exact_plan(
            self.seed,
            self.demand,
            self.frequency,
            self.banks,
            self.exact,
            self.provenance,
        )
        self.assertEqual(repeated, self.canonical)
        self.assertEqual(repeated_report, self.report)

    def test_schedule_identity_must_match_every_planning_artifact(self) -> None:
        mismatched = copy.deepcopy(self.exact)
        mismatched["scheduleId"] = "different_schedule"
        with self.assertRaisesRegex(ValueError, "schedule ID mismatch"):
            build_canonical_schedule_from_exact_plan(
                self.seed,
                self.demand,
                self.frequency,
                self.banks,
                mismatched,
                self.provenance,
            )


if __name__ == "__main__":
    unittest.main()
