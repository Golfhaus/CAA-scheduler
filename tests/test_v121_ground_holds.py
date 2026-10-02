"""Latest v1.2.1 release: approved additions and preservation of its input flying."""
from collections import Counter
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_schedule_7_v1_2_1_holds import BASE, HoldSearch
from analyze_schedule_7_v1_2_1_remaining_holds import find_holds
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.io import read_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.validation import validate_schedule
from latest_schedule import CANONICAL, SCHEDULE_ID


class GroundHoldReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = read_json(ROOT / BASE)
        cls.draft = CANONICAL

    def test_preserves_existing_flying_inventory_and_policies(self):
        after = {l["id"]: l for l in self.draft["legs"]}
        for before in self.base["legs"]:
            old, new = dict(before), dict(after[before["id"]])
            old.pop("sequenceWithinRoute")
            new.pop("sequenceWithinRoute")
            retimings = {2041: 11, 1607: -3, 2043: 7}
            if before["flight"] in retimings:
                self.assertEqual(new["departureMinute"] - old["departureMinute"], retimings[before["flight"]])
                self.assertEqual(new["arrivalMinute"] - old["arrivalMinute"], retimings[before["flight"]])
                for key in ("departureMinute", "arrivalMinute", "departure", "arrival"):
                    old.pop(key)
                    new.pop(key)
            self.assertEqual(new, old)
        for field in ("cities", "hubBanks", "operatingPolicy"):
            self.assertEqual(self.draft[field], self.base[field])
        self.assertEqual({k: v for k, v in self.draft["gatePlan"].items() if k != "label"},
                         {k: v for k, v in self.base["gatePlan"].items() if k != "label"})
        self.assertEqual(self.draft["schedule"]["fleetCounts"], self.base["schedule"]["fleetCounts"])
        for field in ("route", "line"):
            self.assertEqual({l[field] for l in self.draft["legs"]}, {l[field] for l in self.base["legs"]})
        self.assertEqual({(l["fleet"], l["line"], l["day"]) for l in self.draft["legs"]},
                         {(l["fleet"], l["line"], l["day"]) for l in self.base["legs"]})

    def test_frequency_gains_and_published_default(self):
        manifest = read_json(ROOT / "web/schedules.json")
        self.assertEqual(manifest["defaultScheduleId"], "schedule_7_v1_2_1")
        self.assertEqual(SCHEDULE_ID, "schedule_7_v1_2_1")
        self.assertEqual(self.draft["schedule"]["status"], "released")
        self.assertEqual(len(self.draft["legs"]), 1116)
        count = Counter((l["origin"], l["destination"]) for l in self.draft["legs"])
        for a, b, expected in (("PHF", "PGD", 2), ("SYR", "BDL", 2), ("SYR", "RFD", 3), ("MCI", "DAY", 2),
                               ("MCI", "BLV", 3), ("MCI", "XNA", 2), ("SYR", "PIT", 3), ("SYR", "BWI", 2),
                               ("SAT", "MCI", 3), ("JAN", "MCI", 3)):
            self.assertEqual(count[a, b], expected)
            self.assertEqual(count[b, a], expected)

    def test_physical_operations_planning_and_overnight(self):
        self.assertEqual(validate_schedule(self.draft)["status"], "pass")
        operating = validate_operating_rules(self.draft)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]))
        self.assertEqual(validate_overnight_turns(self.draft)["status"], "pass")
        self.assertEqual(validate_planning_snapshot(reconstruct_planning_snapshot(self.draft), self.draft)["status"], "pass")
        stands = [p for city in export_gate_schedule(self.draft)["cities"] for p in city["claims"] if p["rowType"] == "stand"]
        self.assertEqual((len(stands), sum(p["end"] - p["start"] for p in stands)), (15, 4277))
        self.assertFalse(any(p["label"] in {"701", "123", "321", "147", "323"} for p in stands))

    def test_screen_reconciles_to_full_single_round_trip_allocation(self):
        search = HoldSearch(self.draft)
        added = [search.leg("PHF", "PGD", 560, "MAX9", "TEST-OUT"),
                 search.leg("PGD", "PHF", 760, "MAX9", "TEST-BACK")]
        _, screened = search.score(added)
        loads, _ = search.screen.allocate(search.screen.enumerate(search.base["legs"] + added))
        for leg, expected in zip(added, screened):
            self.assertAlmostEqual(sum(loads[leg["id"]].values()), expected, places=7)

    def test_latest_has_only_two_remaining_hub_holds(self):
        self.assertEqual({h["route"]: h["holdMinutes"] for h in find_holds(self.draft)}, {322: 344, 122: 330})

    def test_exact_approved_routes_and_twenty_new_flights(self):
        expected = [
            (701, "PHF", "PGD", "09:20", "11:21"), (701, "PGD", "PHF", "12:40", "14:41"),
            (123, "SYR", "BDL", "08:40", "09:34"), (123, "BDL", "SYR", "10:30", "11:24"),
            (321, "SYR", "RFD", "16:50", "17:44"), (321, "RFD", "SYR", "18:44", "21:38"),
            (129, "MCI", "DAY", "14:50", "17:35"), (129, "DAY", "MCI", "18:15", "19:00"),
            (118, "MCI", "BLV", "15:25", "16:30"), (118, "BLV", "MCI", "17:10", "18:15"),
            (151, "MCI", "XNA", "13:45", "14:42"), (151, "XNA", "MCI", "15:38", "16:35"),
            (147, "SYR", "PIT", "11:18", "12:24"), (147, "PIT", "SYR", "13:04", "14:10"),
            (323, "SYR", "BWI", "18:55", "20:00"), (323, "BWI", "SYR", "20:40", "21:45"),
            (508, "SAT", "MCI", "20:19", "22:15"), (508, "MCI", "SAT", "22:55", "00:51"),
            (131, "JAN", "MCI", "19:05", "20:48"), (131, "MCI", "JAN", "21:28", "23:11"),
        ]
        added = sorted((l for l in self.draft["legs"] if l["id"] not in {b["id"] for b in self.base["legs"]}),
                       key=lambda l:l["flight"])
        self.assertEqual([l["flight"] for l in added], list(range(2099, 2119)))
        self.assertEqual([tuple(l[k] for k in ("route","origin","destination","departure","arrival"))
                          for l in added], expected)
        self.assertEqual({l["route"] for l in added}, {701,123,321,129,118,323,147,151,508,131})
        self.assertEqual(next(l for l in added if l["flight"] == 2116)["arrivalMinute"], 1491)

    def test_early_BWI_option_is_rejected_by_full_gate_rules(self):
        search = HoldSearch(self.draft)
        trial = search.overlay({322: {"legs": [search.leg("SYR", "BWI", 465, "CRJ700"),
                                                search.leg("BWI", "SYR", 575, "CRJ700")]}})
        candidate = apply_optimization_overlay(self.draft, trial)
        operating = validate_operating_rules(candidate)
        self.assertTrue(any(c["id"] == "fixed_physical_inventory" and c["status"] == "fail"
                            for c in operating["checks"]))


if __name__ == "__main__":
    unittest.main()
