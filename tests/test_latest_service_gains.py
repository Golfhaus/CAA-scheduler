"""Latest released flying, trunk availability, physical gates and two-stop accounting."""
from collections import Counter
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from latest_schedule import CANONICAL, SCHEDULE_ID
from build_schedule_7_v1_2_two_day_growth import TwoStopScreen
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.validation import validate_schedule


class TwoDayGrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = CANONICAL

    def test_released_sequence_and_consolidated_lines(self):
        self.assertEqual(SCHEDULE_ID, "schedule_7_v1_2_3")
        self.assertEqual(self.candidate["schedule"]["status"], "released")
        self.assertEqual(len(self.candidate["legs"]), 1152)
        new = sorted((l for l in self.candidate["legs"] if l["id"].startswith("V120-2MAX-")),
                     key=lambda l: l["flight"])
        self.assertEqual([l["flight"] for l in new], list(range(2083, 2099)))
        self.assertEqual([(l["origin"], l["destination"]) for l in new], [
            ("SFB", "JAX"), ("JAX", "DAY"), ("DAY", "CAK"), ("CAK", "DAY"),
            ("DAY", "JAX"), ("JAX", "FLL"), ("FLL", "JAX"), ("JAX", "DAY"),
            ("DAY", "JAX"), ("JAX", "DAY"), ("DAY", "CMH"), ("CMH", "DAY"),
            ("DAY", "IND"), ("IND", "DAY"), ("DAY", "JAX"), ("JAX", "SFB")])
        self.assertEqual([(l["departure"], l["arrival"]) for l in new], [
            ("04:30", "05:18"), ("06:15", "08:04"), ("09:10", "10:02"), ("10:42", "11:34"),
            ("12:14", "14:03"), ("14:50", "16:00"), ("16:40", "17:50"), ("18:36", "20:25"),
            ("05:09", "06:58"), ("07:38", "09:27"), ("10:07", "10:49"), ("11:29", "12:11"),
            ("13:20", "14:07"), ("14:47", "15:34"), ("16:16", "18:05"), ("18:47", "19:35")])
        self.assertTrue(all((l["fleet"], l["line"], l["route"], l["day"]) ==
                            ("MAX9", "A", 703 + i // 8, 3 + i // 8) for i, l in enumerate(new)))
        for fleet, expected in (("MAX9", {"A": 13, "B": 10}), ("CRJ900", {"AB": 10, "AG": 9, "AJ": 9})):
            days = {(l["line"], l["day"]) for l in self.candidate["legs"] if l["fleet"] == fleet}
            self.assertEqual(Counter(line for line, _ in days), expected)
        self.assertEqual(self.candidate["schedule"]["fleetCounts"]["MAX9"], 35)

    def test_daily_frequencies_meet_the_requested_priority(self):
        count = Counter((l["origin"], l["destination"]) for l in self.candidate["legs"])
        self.assertEqual(count["DAY", "JAX"], 4)
        self.assertEqual(count["JAX", "DAY"], 4)
        for hub, city in (("JAX", "SFB"), ("JAX", "FLL"), ("DAY", "CMH"), ("DAY", "CAK"), ("DAY", "IND")):
            expected = 3 if (hub, city) == ("JAX", "SFB") else 2
            self.assertEqual(count[hub, city], expected)
            self.assertEqual(count[city, hub], expected)
        self.assertEqual(count["DAY", "RFD"], 3)
        self.assertEqual(count["RFD", "DAY"], 3)
        for origin, destination in (("DAY", "JAX"), ("JAX", "DAY")):
            times = sorted(l["departureMinute"] for l in self.candidate["legs"]
                           if (l["origin"], l["destination"]) == (origin, destination))
            self.assertTrue(all((b - a) % 1440 >= 30 for a, b in zip(times, times[1:] + times[:1])))

    def test_operating_planning_and_overnight_checks_and_no_extra_stand_use(self):
        self.assertEqual(validate_schedule(self.candidate)["status"], "pass")
        operating = validate_operating_rules(self.candidate)
        self.assertEqual(operating["summary"]["effectiveErrorFindings"], 0)
        self.assertFalse(any(c["hardStop"] and c["status"] == "fail" for c in operating["checks"]))
        self.assertEqual(validate_overnight_turns(self.candidate)["status"], "pass")
        self.assertEqual(validate_planning_snapshot(reconstruct_planning_snapshot(self.candidate), self.candidate)["status"], "pass")
        counts = next(c for c in operating["checks"] if c["id"] == "line_route_count")
        self.assertTrue(any(f["evidence"]["line"] == "A" and f["evidence"]["routes"] == 13 for f in counts["findings"]))
        for schedule in (self.candidate,):
            stands = [p for city in export_gate_schedule(schedule)["cities"] for p in city["claims"] if p["rowType"] == "stand"]
            self.assertEqual((len(stands), sum(p["end"] - p["start"] for p in stands)), (15, 3771))

    def test_two_stop_middle_leg_is_counted_once_and_demand_reconciles(self):
        screen = TwoStopScreen(self.candidate)
        flights = [l for l in self.candidate["legs"] if l["id"] in
                   {"V120-2MAX-D1-1-SFB-JAX", "V120-2MAX-D1-2-JAX-DAY", "V120-2MAX-D1-3-DAY-CAK"}]
        options = screen.enumerate(flights)
        choices = options["SFB", "CAK"]
        self.assertEqual(len(choices), 1)
        self.assertEqual(len(choices[0]["legs"]), 3)
        loads, records = screen.allocate(options)
        middle = "V120-2MAX-D1-2-JAX-DAY"
        self.assertAlmostEqual(loads[middle]["through"], screen.od["SFB"]["CAK"])
        through = [r for r in records[middle] if (r["origin"], r["destination"]) == ("SFB", "CAK")]
        self.assertEqual(len(through), 1)
        self.assertEqual(through[0]["side"], "through")
        self.assertEqual(through[0]["stops"], 2)

    def test_overnight_turn_check_rejects_a_late_arrival_in_the_current_rotation(self):
        report = validate_overnight_turns(self.candidate)
        transition = min(report["metrics"]["transitions"], key=lambda t: t["minutes"])
        self.assertGreaterEqual(transition["minutes"], 40)
        self.assertLess(transition["minutes"], 45)
        late = copy.deepcopy(self.candidate)
        last = max((l for l in late["legs"] if l["route"] == transition["fromRoute"]),
                   key=lambda l: l["sequenceWithinRoute"])
        last["arrivalMinute"] += 5
        self.assertEqual(validate_overnight_turns(late)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
