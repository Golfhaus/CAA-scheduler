from collections import Counter, defaultdict
import copy
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.io import read_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.validation import validate_schedule


@unittest.skip("Superseded schedule or feasibility checkpoint; regression targets the latest release")
class V120Crj900LineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = read_json(REPO_ROOT / "data/schedules/schedule_7_v1_1_6/canonical_schedule.json")
        cls.overlay = read_json(REPO_ROOT / "config/optimizations/schedule_7_v1_2_0_round_1.json")
        cls.candidate = apply_optimization_overlay(cls.base, cls.overlay)

    def test_only_approved_flight_and_route_changes(self):
        baseline = copy.deepcopy(self.base)
        self.assertEqual(apply_optimization_overlay(self.base, self.overlay), self.candidate)
        self.assertEqual(self.base, baseline)
        actual = {l["id"]: l for l in self.candidate["legs"]}
        self.assertEqual(set(actual), {l["id"] for l in self.base["legs"]})
        for old in self.base["legs"]:
            new = actual[old["id"]]
            if old["fleet"] != "CRJ900":
                self.assertEqual(old, new)
                continue
            for key in ["flight", "pairing", "fleet", "origin", "destination"]:
                self.assertEqual(old[key], new[key])
            shift = 10 if old["id"] == "ABE-SFB-CRJ900-01-IN" else 0
            self.assertEqual(new["departureMinute"], old["departureMinute"] + shift)
            self.assertEqual(new["arrivalMinute"], old["arrivalMinute"] + shift)
        for key in ["operatingPolicy", "hubBanks", "bankAssignments", "cities"]:
            self.assertEqual(self.base[key], self.candidate[key])
        self.assertEqual(self.base["schedule"]["fleetCounts"], self.candidate["schedule"]["fleetCounts"])
        self.assertEqual(self.candidate["schedule"]["status"], "draft")
        self.assertEqual(read_json(REPO_ROOT / "web/schedules.json")["defaultScheduleId"], "schedule_7_v1_1_6")

    def test_lines_close_with_hub_rons_and_sequential_route_numbers(self):
        routes = defaultdict(list)
        for leg in self.candidate["legs"]:
            if leg["fleet"] == "CRJ900":
                routes[leg["route"]].append(leg)
        self.assertEqual(len(routes), 28)
        lines = defaultdict(list)
        for r, legs in routes.items():
            legs.sort(key=lambda l: l["sequenceWithinRoute"])
            lines[legs[0]["line"]].append((legs[0]["day"], r, legs))
        self.assertEqual({k: len(v) for k, v in lines.items()}, {"AB": 10, "AG": 9, "AJ": 9})
        hubs = set(self.candidate["operatingPolicy"]["hubs"] + self.candidate["operatingPolicy"]["focusCities"])
        for line, rows in lines.items():
            rows.sort()
            numbers = [r for _, r, _ in rows]
            self.assertEqual(numbers, list(range(min(numbers), max(numbers) + 1)))
            self.assertTrue(any(ls[-1]["destination"] in hubs for _, _, ls in rows))
            for i, (_, _, ls) in enumerate(rows):
                following = rows[(i + 1) % len(rows)][2]
                self.assertEqual(ls[-1]["destination"], following[0]["origin"])

    def test_operating_planning_and_fixed_capacity(self):
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]))
        for c in operating["checks"]:
            if c["id"] == "line_route_count":
                self.assertFalse(any(f["evidence"]["line"] in {"AB", "AG", "AJ"} for f in c["findings"]))
        planning = reconstruct_planning_snapshot(self.candidate)
        self.assertEqual(validate_planning_snapshot(planning, self.candidate)["status"], "pass")
        stands = [s for city in export_gate_schedule(self.candidate)["cities"] for s in city["claims"] if s["rowType"] == "stand"]
        self.assertEqual((len(stands), sum(s["end"] - s["start"] for s in stands)), (21, 6188))

    def test_exchange_guards_reject_stale_duplicate_and_cross_fleet_moves(self):
        for kind in ["stale", "duplicate", "fleet"]:
            overlay = copy.deepcopy(self.overlay)
            first = overlay["legReassignments"][0]
            if kind == "stale":
                first["expectedRoute"] = 999
            elif kind == "duplicate":
                overlay["legReassignments"].append(copy.deepcopy(first))
            else:
                first["targetRoute"] = 101
            with self.assertRaises(ValueError):
                apply_optimization_overlay(self.base, overlay)


if __name__ == "__main__":
    unittest.main()
