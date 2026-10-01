import copy
from collections import Counter
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import read_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.validation import validate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot


@unittest.skip("Superseded schedule or feasibility checkpoint; regression targets the latest release")
class V120Max9LineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.released = read_json(REPO_ROOT / "data/schedules/schedule_7_v1_1_6/canonical_schedule.json")
        cls.base = apply_optimization_overlay(cls.released, read_json(REPO_ROOT / "config/optimizations/schedule_7_v1_2_0_round_1.json"))
        cls.overlay = read_json(REPO_ROOT / "config/optimizations/schedule_7_v1_2_0_round_2.json")
        cls.candidate = apply_optimization_overlay(cls.base, cls.overlay)

    def test_flight_sequences_and_all_non_rotation_fields_are_preserved(self):
        self.assertEqual(self.candidate, apply_optimization_overlay(self.base, self.overlay))
        ignored = {"route", "line", "day"}
        for old, new in zip(self.base["legs"], self.candidate["legs"]):
            self.assertEqual({k: v for k, v in old.items() if k not in ignored},
                             {k: v for k, v in new.items() if k not in ignored})
            if old["fleet"] != "MAX9":
                self.assertEqual(old, new)
        for key in ["cities", "operatingPolicy", "hubBanks", "bankAssignments"]:
            self.assertEqual(self.base[key], self.candidate[key])
        self.assertEqual(self.base["schedule"]["fleetCounts"], self.candidate["schedule"]["fleetCounts"])
        self.assertEqual(self.candidate["schedule"]["status"], "draft")
        self.assertEqual(read_json(REPO_ROOT / "web/schedules.json")["defaultScheduleId"], "schedule_7_v1_1_6")

    def test_compliant_closed_lines_and_capacity(self):
        lengths = Counter(line for line, day in {(l["line"], l["day"]) for l in self.candidate["legs"] if l["fleet"] == "MAX9"})
        self.assertEqual(lengths, {"A": 11, "B": 10})
        self.assertEqual(len({l["line"] for l in self.candidate["legs"]}), 20)
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]))
        self.assertEqual(validate_planning_snapshot(reconstruct_planning_snapshot(self.candidate), self.candidate)["status"], "pass")
        stands = [s for city in export_gate_schedule(self.candidate)["cities"] for s in city["claims"] if s["rowType"] == "stand"]
        self.assertEqual((len(stands), sum(s["end"] - s["start"] for s in stands)), (20, 5552))

    def test_real_next_day_turn_closes_the_baseline_validation_gap(self):
        old = validate_overnight_turns(self.released)
        self.assertEqual(old["status"], "fail")
        self.assertEqual(len(old["findings"]), 1)
        finding = old["findings"][0]["evidence"]
        self.assertEqual((finding["fromRoute"], finding["toRoute"], finding["minutes"]), (713, 717, -2))
        check = validate_overnight_turns(self.candidate)
        self.assertEqual(check["status"], "pass")
        transition = next(t for t in check["metrics"]["transitions"] if t["fromRoute"] == 708)
        self.assertEqual((transition["toRoute"], transition["city"], transition["minutes"]), (709, "PIE", 43))
        late = copy.deepcopy(self.candidate)
        legs = [l for l in late["legs"] if l["route"] == 708]
        max(legs, key=lambda l: l["sequenceWithinRoute"])["arrivalMinute"] += 5
        failed = validate_overnight_turns(late)
        self.assertEqual(failed["status"], "fail")
        self.assertEqual(failed["findings"][0]["evidence"]["minutes"], 38)


if __name__ == "__main__":
    unittest.main()
