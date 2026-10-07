"""Latest approved utilization flying, bank changes and input preservation."""
import copy
import json
from pathlib import Path
import unittest
from latest_schedule import CANONICAL, SCHEDULE_ID

ROOT = Path(__file__).resolve().parents[1]


class LatestApprovedFlyingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((ROOT / 'data/schedules/schedule_7_v1_2_2/canonical_schedule.json').read_text())
        cls.first = json.loads((ROOT / 'config/optimizations/schedule_7_v1_2_3_accepted_rounds_1_3.json').read_text())
        cls.last = json.loads((ROOT / 'config/optimizations/schedule_7_v1_2_3_round_4.json').read_text())

    def test_exact_approved_additions(self):
        self.assertEqual(SCHEDULE_ID, 'schedule_7_v1_2_3')
        old_ids = {l['id'] for l in self.base['legs']}
        added = sorted((l for l in CANONICAL['legs'] if l['id'] not in old_ids), key=lambda l:l['flight'])
        self.assertEqual([l['flight'] for l in added], list(range(2131, 2155)))
        self.assertEqual([tuple(l[k] for k in ('route','origin','destination','departure','arrival')) for l in added], [
            (331,'BWI','DAY','05:43','07:05'), (331,'DAY','BWI','07:53','09:15'),
            (331,'BWI','DAY','19:52','21:14'), (331,'DAY','BWI','21:54','23:16'),
            (340,'CLT','DAY','19:48','21:05'), (340,'DAY','CLT','21:55','23:12'),
            (327,'SDF','DAY','20:17','21:05'), (327,'DAY','SDF','21:55','22:43'),
            (327,'PGD','JAX','05:55','06:57'), (327,'JAX','PGD','08:00','09:02'),
            (145,'PWM','PHF','04:40','06:24'), (145,'PHF','PWM','07:04','08:48'),
            (145,'SYR','BUF','11:18','12:04'), (145,'BUF','SYR','12:44','13:30'),
            (305,'MCI','TUL','09:46','10:44'), (305,'TUL','MCI','11:25','12:23'),
            (526,'DAL','MCI','04:58','06:25'), (526,'MCI','DAL','07:15','08:42'),
            (509,'SAT','DAL','05:00','06:01'), (509,'DAL','SAT','06:51','07:52'),
            (114,'ROA','PHF','19:30','20:24'), (114,'PHF','ROA','21:45','22:39'),
            (169,'FWA','DAY','20:25','21:05'), (169,'DAY','FWA','21:55','22:35')])
        self.assertFalse(any(l['route'] in {163,350} for l in added))

    def test_only_authorized_retimings_and_no_aircraft_changes(self):
        after = {l['id']:l for l in CANONICAL['legs']}
        changes = {r['legId']:r for r in self.first['retimeLegs'] + self.last['retimeLegs']}
        self.assertEqual({after[i]['route']:r['departureMinute']-r['expectedDepartureMinute'] for i,r in changes.items()}, {145:5,305:-191,526:12})
        for before in self.base['legs']:
            old, new = dict(before), dict(after[before['id']])
            old.pop('sequenceWithinRoute'); new.pop('sequenceWithinRoute')
            if before['id'] in changes:
                for key in ('departureMinute','arrivalMinute'):
                    self.assertEqual(new[key],changes[before['id']][key])
                for key in ('departureMinute','arrivalMinute','departure','arrival'):
                    old.pop(key); new.pop(key)
            self.assertEqual(new, old)
        self.assertEqual(CANONICAL['cities'], self.base['cities'])
        self.assertEqual(CANONICAL['schedule']['fleetCounts'], self.base['schedule']['fleetCounts'])
        self.assertEqual({(l['fleet'],l['line'],l['day']) for l in CANONICAL['legs']},
                         {(l['fleet'],l['line'],l['day']) for l in self.base['legs']})
        self.assertEqual({k:v for k,v in CANONICAL['gatePlan'].items() if k!='label'},
                         {k:v for k,v in self.base['gatePlan'].items() if k!='label'})

    def test_only_approved_bank_and_policy_change(self):
        expected_banks=copy.deepcopy(self.base['hubBanks'])
        bank=next(b for b in expected_banks if b['id']=='MCI-B3')
        bank.update(startMinute=487,endMinute=547)
        expected_banks.append({'id':'DAY-B9','hub':'DAY','startMinute':1265,'endMinute':1325})
        self.assertEqual(CANONICAL['hubBanks'],expected_banks)
        expected=copy.deepcopy(self.base['operatingPolicy'])
        expected['hubBankCounts']['DAY']=9
        expected['overrides']+=self.last['operatingOverrides']
        self.assertEqual(CANONICAL['operatingPolicy'],expected)
        self.assertEqual([(o['checkId'],o['findingId']) for o in self.last['operatingOverrides']], [('tiered_service_minimums','ROA')])
        legs={l['flight']:l for l in CANONICAL['legs']}
        inbound,outbound=legs[2153],legs[2154]
        self.assertEqual(outbound['departureMinute']-inbound['arrivalMinute'],50)
        for l in (inbound,outbound):
            assignments=[a for a in CANONICAL['bankAssignments'] if a['legId']==l['id']]
            self.assertEqual([a['bankId'] for a in assignments],['DAY-B9'])
        roa=legs[2151]
        wave=[l for l in CANONICAL['legs'] if l['origin']=='PHF' and l['departureMinute']==1255]
        self.assertGreater(len(wave),8)
        self.assertTrue(all(l['departureMinute']-roa['arrivalMinute']==31 for l in wave))


if __name__ == '__main__':
    unittest.main()
