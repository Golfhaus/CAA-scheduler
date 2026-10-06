"""Approved v1.2.2 flying and preservation of its released input schedule."""
import copy
import json
from pathlib import Path
import unittest
from latest_schedule import CANONICAL, SCHEDULE_ID

ROOT = Path(__file__).resolve().parents[1]


class LatestJaxBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((ROOT / 'data/schedules/schedule_7_v1_2_1/canonical_schedule.json').read_text())
        cls.overlay = json.loads((ROOT / 'config/optimizations/schedule_7_v1_2_2_round_1.json').read_text())

    def test_exact_approved_additions(self):
        self.assertEqual(SCHEDULE_ID, 'schedule_7_v1_2_2')
        old_ids = {l['id'] for l in self.base['legs']}
        added = sorted((l for l in CANONICAL['legs'] if l['id'] not in old_ids), key=lambda l:l['flight'])
        self.assertEqual([l['flight'] for l in added], list(range(2119, 2131)))
        self.assertEqual([tuple(l[k] for k in ('route','origin','destination','departure','arrival')) for l in added], [
            (702,'SFB','JAX','20:05','20:53'), (702,'JAX','SFB','21:33','22:21'),
            (704,'SFB','BHM','20:19','20:45'), (704,'BHM','SFB','23:15','01:41'),
            (341,'MSY','JAX','18:24','20:59'), (341,'JAX','MSY','21:39','22:14'),
            (504,'CLT','JAX','19:34','20:45'), (504,'JAX','CLT','21:25','22:36'),
            (338,'SAV','JAX','20:00','20:45'), (338,'JAX','SAV','21:25','22:10'),
            (514,'PIE','JAX','20:14','21:08'), (515,'JAX','PIE','06:20','07:14')])

    def test_only_authorized_retimings_and_no_aircraft_changes(self):
        after = {l['id']:l for l in CANONICAL['legs']}
        retimed = {r['legId'] for r in self.overlay['retimeLegs']}
        self.assertEqual(len(retimed), 2)
        for before in self.base['legs']:
            old, new = dict(before), dict(after[before['id']])
            old.pop('sequenceWithinRoute'); new.pop('sequenceWithinRoute')
            if before['id'] in retimed:
                self.assertEqual(before['route'], 515)
                for key in ('departureMinute','arrivalMinute'):
                    self.assertEqual(new[key]-old[key], 9)
                for key in ('departureMinute','arrivalMinute','departure','arrival'):
                    old.pop(key); new.pop(key)
            self.assertEqual(new, old)
        for field in ('cities',):
            self.assertEqual(CANONICAL[field], self.base[field])
        self.assertEqual(CANONICAL['schedule']['fleetCounts'], self.base['schedule']['fleetCounts'])
        self.assertEqual({(l['fleet'],l['line'],l['day']) for l in CANONICAL['legs']},
                         {(l['fleet'],l['line'],l['day']) for l in self.base['legs']})
        self.assertEqual({k:v for k,v in CANONICAL['gatePlan'].items() if k!='label'},
                         {k:v for k,v in self.base['gatePlan'].items() if k!='label'})

    def test_only_approved_bank_and_policy_change(self):
        self.assertEqual(CANONICAL['hubBanks'], self.base['hubBanks'] + self.overlay['hubBanksToAdd'])
        expected = copy.deepcopy(self.base['operatingPolicy'])
        expected['hubBankCounts']['JAX'] = 15
        self.assertEqual(CANONICAL['operatingPolicy'], expected)
        self.assertFalse(self.overlay['operatingOverrides'])
        banks = [b for b in CANONICAL['hubBanks'] if b['id']=='JAX-B15']
        self.assertEqual([(b['startMinute'],b['endMinute']) for b in banks], [(1245,1305)])


if __name__ == '__main__':
    unittest.main()
