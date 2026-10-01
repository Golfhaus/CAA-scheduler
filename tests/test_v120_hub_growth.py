"""Ground feasibility and additive-scope regression for one-spare-MAX9 options."""
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_schedule_7_v1_2_hub_growth import baseline
from caa_scheduler.io import read_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.validation import validate_schedule


@unittest.skip("Superseded schedule or feasibility checkpoint; regression targets the latest release")
class HubGrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = baseline()

    def test_alternatives_preserve_existing_service_and_use_one_spare(self):
        for name, added in (("jax_core", 6), ("jax_pgd", 8), ("jax_day_rfd", 6)):
            with self.subTest(name=name):
                overlay = read_json(ROOT / f"config/proposals/schedule_7_v1_2_0_{name}.json")
                candidate = apply_optimization_overlay(self.base, overlay)
                old = {l["id"]: l for l in self.base["legs"]}
                current = {l["id"]: l for l in candidate["legs"]}
                self.assertEqual(len(current), len(old) + added)
                ignored = {"route", "day"}
                for identifier, leg in old.items():
                    self.assertEqual({k: v for k, v in leg.items() if k not in ignored},
                                     {k: v for k, v in current[identifier].items() if k not in ignored})
                for key in ("cities", "operatingPolicy", "hubBanks"):
                    self.assertEqual(candidate[key], self.base[key])
                self.assertEqual(candidate["schedule"]["fleetCounts"], self.base["schedule"]["fleetCounts"])
                days = {(l["line"], l["day"]) for l in current.values() if l["fleet"] == "MAX9"}
                self.assertEqual(Counter(line for line, _ in days), {"A": 12, "B": 10})
                self.assertEqual(len(days), 22)
                self.assertEqual(candidate["schedule"]["status"], "draft")
                for assignment in self.base["bankAssignments"]:
                    self.assertIn(assignment, candidate["bankAssignments"])
                self.assertEqual(validate_schedule(candidate)["status"], "pass")
                operating = validate_operating_rules(candidate)
                self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
                self.assertFalse(any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]))
                self.assertEqual(validate_overnight_turns(candidate)["status"], "pass")
                self.assertEqual(validate_planning_snapshot(reconstruct_planning_snapshot(candidate), candidate)["status"], "pass")
        self.assertEqual(read_json(ROOT / "web/schedules.json")["defaultScheduleId"], "schedule_7_v1_1_6")


if __name__ == "__main__":
    unittest.main()
