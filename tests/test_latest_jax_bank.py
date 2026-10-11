"""Latest approved additions, source preservation, alignment and bank changes."""
from collections import Counter
import copy
import json
from pathlib import Path
import unittest
from latest_schedule import CANONICAL,SCHEDULE_ID
ROOT=Path(__file__).resolve().parents[1]

class LatestApprovedFlyingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=json.loads((ROOT/'data/schedules/schedule_7_v1_2_4/canonical_schedule.json').read_text())
        cls.overlay=json.loads((ROOT/'config/optimizations/schedule_7_v1_2_5_accepted_rounds_1_3.json').read_text())

    def test_exact_approved_additions(self):
        self.assertEqual(SCHEDULE_ID,'schedule_7_v1_2_5')
        old_ids={l['id'] for l in self.base['legs']}
        added=sorted((l for l in CANONICAL['legs'] if l['id'] not in old_ids),key=lambda l:l['flight'])
        self.assertEqual([l['flight'] for l in added],list(range(2173,2193)))
        self.assertEqual([tuple(l[k] for k in ('route','line','day','origin','destination','departureMinute','arrivalMinute')) for l in added],[
            (125,'AE',4,'DAY','IND',1295,1338),(126,'AE',5,'IND','DAY',270,313),
            (136,'AF',4,'DAY','CAK',1295,1345),(137,'AF',5,'CAK','DAY',270,320),
            (112,'AD',2,'MCI','SDF',1270,1425),(113,'AD',3,'SDF','MCI',270,305),
            (135,'AF',3,'MCI','SBN',1285,1438),(136,'AF',4,'SBN','MCI',270,303),
            (715,'B',2,'MCI','GRR',1283,1438),(716,'B',3,'GRR','MCI',270,305),
            (323,'AK',3,'MCI','SGF',1390,1440),(324,'AK',4,'SGF','MCI',270,320),
            (159,'AM',4,'ALB','PHF',615,700),(159,'AM',4,'PHF','ALB',800,885),
            (130,'AE',9,'SWF','PHF',480,553),(130,'AE',9,'PHF','SWF',605,678),
            (318,'AH',7,'SYR','BTV',465,517),(318,'AH',7,'BTV','SYR',588,640),
            (161,'AM',6,'SYR','HPN',465,519),(161,'AM',6,'HPN','SYR',576,630)])
        count=Counter((l['origin'],l['destination']) for l in CANONICAL['legs'])
        for hub,city,n in [('MCI','SDF',3),('MCI','SBN',2),('MCI','GRR',1),('MCI','SGF',2),('ALB','PHF',2),('SWF','PHF',1),('SYR','BTV',4),('SYR','HPN',4)]:
            self.assertEqual((count[hub,city],count[city,hub]),(n,n))
        for route in (159,130,318,161):
            legs=sorted((l for l in CANONICAL['legs'] if l['route']==route),key=lambda l:l['sequenceWithinRoute'])
            self.assertLess(max(b['departureMinute']-a['arrivalMinute'] for a,b in zip(legs,legs[1:])),330)

    def test_only_authorized_retimings_and_no_aircraft_changes(self):
        after={l['id']:l for l in CANONICAL['legs']};changes={r['legId']:r for r in self.overlay['retimeLegs']}
        self.assertEqual({after[i]['flight']:r['departureMinute']-r['expectedDepartureMinute'] for i,r in changes.items()},
            {1503:3,1873:10,1595:15,1715:15,1035:15,2002:6,1083:3,1139:15,1405:15,1633:15,1647:15,1675:15,1886:2,2011:2,2095:2,2096:2})
        moved={r['legId']:r for r in self.overlay['legReassignments']};mapping={r['sourceRoute']:r for r in self.overlay['routeReassignments']}
        identities={l['route']:(l['line'],l['day'],l['fleet']) for l in self.base['legs']}
        for before in self.base['legs']:
            old,new=dict(before),dict(after[before['id']]);old.pop('sequenceWithinRoute');new.pop('sequenceWithinRoute')
            if before['id'] in moved:
                target=moved[before['id']]['targetRoute'];line,day,fleet=identities[target];old.update(route=target,line=line,day=day,fleet=fleet)
            if old['route'] in mapping:
                m=mapping[old['route']];old.update(route=m['targetRoute'],line=m['line'],day=m['day'])
            if before['id'] in changes:
                for key in ('departureMinute','arrivalMinute'):self.assertEqual(new[key],changes[before['id']][key])
                for key in ('departureMinute','arrivalMinute','departure','arrival'):old.pop(key);new.pop(key)
            self.assertEqual(new,old)
        self.assertEqual(CANONICAL['cities'],self.base['cities']);self.assertEqual(CANONICAL['schedule']['fleetCounts'],self.base['schedule']['fleetCounts'])
        for fleet in CANONICAL['schedule']['fleetCounts']:
            self.assertEqual(len({(l['line'],l['day']) for l in CANONICAL['legs'] if l['fleet']==fleet}),len({(l['line'],l['day']) for l in self.base['legs'] if l['fleet']==fleet}))
        lengths={line:len({l['day'] for l in CANONICAL['legs'] if l['line']==line}) for line in ('AD','AE','AF','AI','AM','AN')}
        self.assertEqual(lengths,{'AD':11,'AE':11,'AF':11,'AI':12,'AM':12,'AN':9})
        self.assertFalse(any(l['line']=='AR' for l in CANONICAL['legs']))
        self.assertEqual({k:v for k,v in CANONICAL['gatePlan'].items() if k!='label'},{k:v for k,v in self.base['gatePlan'].items() if k!='label'})

    def test_only_approved_bank_and_policy_change(self):
        expected_banks=copy.deepcopy(self.base['hubBanks'])
        for bank_id,start,end in [('DAY-B1',301,361),('MCI-B1',291,351),('DAY-B5',802,862)]:
            next(b for b in expected_banks if b['id']==bank_id).update(startMinute=start,endMinute=end)
        self.assertEqual(CANONICAL['hubBanks'],expected_banks)
        expected=copy.deepcopy(self.base['operatingPolicy']);expected['overrides']+=self.overlay['operatingOverrides'];self.assertEqual(CANONICAL['operatingPolicy'],expected)
        self.assertEqual([(o['checkId'],o['findingId']) for o in self.overlay['operatingOverrides']],[])
        legs={l['flight']:l for l in CANONICAL['legs']}
        self.assertEqual(legs[1886]['departureMinute']-legs[2192]['arrivalMinute'],40)
        self.assertEqual(legs[1297]['departureMinute']-legs[2190]['arrivalMinute'],40)
        self.assertEqual(legs[2097]['departureMinute']-legs[2096]['arrivalMinute'],40)
        for number in (2178,2180,2182,2184):
            self.assertEqual([a['bankId'] for a in CANONICAL['bankAssignments'] if a['legId']==legs[number]['id'] and a['operation']=='arrival'],['MCI-B1'])
        rons={route:max((l for l in CANONICAL['legs'] if l['route']==route),key=lambda l:l['sequenceWithinRoute'])['destination'] for route in (125,136,113,138)}
        self.assertEqual(rons,{125:'IND',136:'CAK',113:'MCI',138:'DAY'})

if __name__=='__main__':unittest.main()
