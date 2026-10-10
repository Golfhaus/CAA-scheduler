"""Latest approved flying, midnight exchange, bank changes and input preservation."""
from collections import Counter
import copy
import json
from pathlib import Path
import unittest
from latest_schedule import CANONICAL, SCHEDULE_ID

ROOT = Path(__file__).resolve().parents[1]


class LatestApprovedFlyingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((ROOT / 'data/schedules/schedule_7_v1_2_3/canonical_schedule.json').read_text())
        cls.overlay = json.loads((ROOT / 'config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_5.json').read_text())

    def test_exact_approved_additions(self):
        self.assertEqual(SCHEDULE_ID, 'schedule_7_v1_2_4')
        old_ids = {l['id'] for l in self.base['legs']}
        added = sorted((l for l in CANONICAL['legs'] if l['id'] not in old_ids), key=lambda l:l['flight'])
        self.assertEqual([l['flight'] for l in added], list(range(2155, 2173)))
        self.assertEqual([tuple(l[k] for k in ('route','line','day','origin','destination','departureMinute','arrivalMinute')) for l in added], [
            (350,'AO',1,'ELP','MCI',1107,1303), (350,'AO',1,'MCI','ELP',1353,1429),
            (126,'AD',16,'MLB','JAX',1200,1252), (126,'AD',16,'JAX','MLB',1302,1354),
            (308,'AA',8,'CLT','MCI',1230,1303), (308,'AA',8,'MCI','CLT',1365,1558),
            (115,'AD',5,'GNV','JAX',1242,1279), (116,'AD',6,'JAX','GNV',270,307),
            (116,'AD',6,'MCI','XNA',1285,1342), (117,'AD',7,'XNA','MCI',330,387),
            (517,'AG',7,'PHF','GNV',1305,1410), (518,'AG',8,'GNV','PHF',270,375),
            (125,'AD',15,'SYR','ROC',366,405), (125,'AD',15,'ROC','SYR',445,484),
            (157,'AE',7,'OMA','BHM',1230,1358), (157,'AE',7,'BHM','OMA',1403,1531),
            (323,'AK',3,'PHF','MCI',1245,1342), (337,'AL',8,'MCI','PHF',1224,1441)])
        count = Counter((l['origin'],l['destination']) for l in CANONICAL['legs'])
        self.assertEqual((count['PHF','MCI'],count['MCI','PHF']),(2,2))
        self.assertEqual((count['OMA','BHM'],count['BHM','OMA']),(2,2))
        self.assertTrue(all(l['arrivalMinute'] <= 1441 for l in added if l['flight'] >= 2171))

    def test_only_authorized_retimings_and_no_aircraft_changes(self):
        after = {l['id']:l for l in CANONICAL['legs']}
        changes = {r['legId']:r for r in self.overlay['retimeLegs']}
        self.assertEqual({after[i]['flight']:r['departureMinute']-r['expectedDepartureMinute'] for i,r in changes.items()},
                         {1739:37,1811:9,1404:-12,1319:-16,1320:-16,1784:-3,1589:-1})
        mapping = {r['sourceRoute']:r for r in self.overlay['routeReassignments']}
        for before in self.base['legs']:
            old, new = dict(before), dict(after[before['id']])
            old.pop('sequenceWithinRoute'); new.pop('sequenceWithinRoute')
            if before['route'] in mapping:
                m = mapping[before['route']]
                old.update(route=m['targetRoute'],line=m['line'],day=m['day'])
            if before['id'] in changes:
                for key in ('departureMinute','arrivalMinute'):
                    self.assertEqual(new[key],changes[before['id']][key])
                for key in ('departureMinute','arrivalMinute','departure','arrival'):
                    old.pop(key); new.pop(key)
            self.assertEqual(new, old)
        self.assertEqual(CANONICAL['cities'], self.base['cities'])
        self.assertEqual(CANONICAL['schedule']['fleetCounts'], self.base['schedule']['fleetCounts'])
        for fleet in CANONICAL['schedule']['fleetCounts']:
            old_days = {(l['line'],l['day']) for l in self.base['legs'] if l['fleet']==fleet}
            new_days = {(l['line'],l['day']) for l in CANONICAL['legs'] if l['fleet']==fleet}
            self.assertEqual(len(new_days),len(old_days))
        lengths = {line:len({l['day'] for l in CANONICAL['legs'] if l['line']==line}) for line in ('AH','AK','AL','AS')}
        self.assertEqual(lengths,{'AH':9,'AK':9,'AL':12,'AS':11})
        self.assertEqual({k:v for k,v in CANONICAL['gatePlan'].items() if k!='label'},
                         {k:v for k,v in self.base['gatePlan'].items() if k!='label'})

    def test_only_approved_bank_and_policy_change(self):
        expected_banks=copy.deepcopy(self.base['hubBanks'])
        next(b for b in expected_banks if b['id']=='MCI-B7').update(startMinute=884,endMinute=944)
        next(b for b in expected_banks if b['id']=='MCI-B10').update(startMinute=1184,endMinute=1244)
        expected_banks.append({'id':'PHF-SWAP-MID-RETIME-337-345-PRESERVE-N1','hub':'PHF','startMinute':0,'endMinute':60})
        self.assertEqual(CANONICAL['hubBanks'],expected_banks)
        expected=copy.deepcopy(self.base['operatingPolicy'])
        expected['hubBankCounts']['PHF']=14
        expected['overrides']+=self.overlay['operatingOverrides']
        self.assertEqual(CANONICAL['operatingPolicy'],expected)
        self.assertEqual([(o['checkId'],o['findingId']) for o in self.overlay['operatingOverrides']], [('tiered_service_minimums','GNV')])
        legs={l['flight']:l for l in CANONICAL['legs']}
        arrival=legs[2172]
        self.assertEqual([a['bankId'] for a in CANONICAL['bankAssignments'] if a['legId']==arrival['id'] and a['operation']=='arrival'],
                         ['PHF-SWAP-MID-RETIME-337-345-PRESERVE-N1'])
        self.assertEqual(legs[1319]['departureMinute']-legs[1784]['arrivalMinute'],30)
        self.assertEqual(legs[1319]['departureMinute']-legs[1589]['arrivalMinute'],30)
        sat=next(l for l in CANONICAL['legs'] if l['origin']=='MCI' and l['destination']=='SAT' and l['departureMinute']==1375)
        self.assertEqual(sat['departureMinute']-legs[2171]['arrivalMinute'],33)


if __name__ == '__main__':
    unittest.main()
