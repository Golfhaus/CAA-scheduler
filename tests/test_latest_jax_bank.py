"""Latest release: exact approved flying, source preservation and connections."""
from collections import Counter
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from latest_schedule import CANONICAL,SCHEDULE_ID
from caa_scheduler.optimization_release import audit_hub_connections

class LatestApprovedFlyingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=json.loads((ROOT/'data/schedules/schedule_7_v1_2_5/canonical_schedule.json').read_text())
        cls.overlay=json.loads((ROOT/'config/optimizations/schedule_7_v1_3_0_round_3.json').read_text())

    def test_exact_approved_r307_additions(self):
        self.assertEqual(SCHEDULE_ID,'schedule_7_v1_3_0')
        old_ids={l['id'] for l in self.base['legs']}
        added=sorted((l for l in CANONICAL['legs'] if l['id'] not in old_ids),key=lambda l:l['flight'])
        self.assertEqual([tuple(l[k] for k in ('flight','route','line','day','origin','destination','departureMinute','arrivalMinute')) for l in added],
                         [(2193,307,'AA',7,'PIT','DAY',758,815),(2194,307,'AA',7,'DAY','PIT',860,917)])
        count=Counter((l['origin'],l['destination']) for l in CANONICAL['legs'])
        self.assertEqual((count['PIT','DAY'],count['DAY','PIT']),(2,2))
        legs={l['flight']:l for l in CANONICAL['legs']}
        self.assertEqual([legs[2193]['departureMinute']-legs[1917]['arrivalMinute'],
                          legs[2194]['departureMinute']-legs[2193]['arrivalMinute'],
                          legs[1918]['departureMinute']-legs[2194]['arrivalMinute']],[74,45,89])
        self.assertEqual((legs[1918]['departure'],legs[1401]['departure']),('16:46','18:35'))

    def test_only_authorized_retimings_and_unchanged_aircraft_days(self):
        after={l['id']:l for l in CANONICAL['legs']}
        changes={r['legId']:r for r in self.overlay['retimeLegs']}
        self.assertEqual({after[i]['flight']:r['departureMinute']-r['expectedDepartureMinute'] for i,r in changes.items()},
                         {1437:-2,1036:-1,2017:-2,2019:-4,1727:8,1723:-1,1589:-3})
        for before in self.base['legs']:
            expected=dict(before)
            if before['id'] in changes:
                r=changes[before['id']]
                expected.update(departureMinute=r['departureMinute'],arrivalMinute=r['arrivalMinute'],
                                departure=after[before['id']]['departure'],arrival=after[before['id']]['arrival'])
            if before['route']==307 and before['sequenceWithinRoute']>=5:
                expected['sequenceWithinRoute']+=2
            self.assertEqual(after[before['id']],expected,before['id'])
        self.assertEqual(CANONICAL['cities'],self.base['cities'])
        self.assertEqual(CANONICAL['schedule']['fleetCounts'],self.base['schedule']['fleetCounts'])
        for fleet in CANONICAL['schedule']['fleetCounts']:
            self.assertEqual({(l['route'],l['line'],l['day']) for l in CANONICAL['legs'] if l['fleet']==fleet},
                             {(l['route'],l['line'],l['day']) for l in self.base['legs'] if l['fleet']==fleet})
        legs={l['flight']:l for l in CANONICAL['legs']}
        self.assertEqual(legs[2019]['departureMinute']-legs[1589]['arrivalMinute'],40)

    def test_banks_policies_and_physical_inventory_are_preserved(self):
        self.assertEqual(CANONICAL['hubBanks'],self.base['hubBanks'])
        self.assertEqual(CANONICAL['operatingPolicy'],self.base['operatingPolicy'])
        self.assertEqual(CANONICAL['bankAssignments'],self.base['bankAssignments']+self.overlay['bankAssignmentsToAdd'])
        self.assertEqual([a['bankId'] for a in self.overlay['bankAssignmentsToAdd']],['DAY-B5','DAY-B5'])
        self.assertEqual({k:v for k,v in CANONICAL['gatePlan'].items() if k!='label'},
                         {k:v for k,v in self.base['gatePlan'].items() if k!='label'})

    def test_requested_one_stop_connections_exist_with_exact_flights(self):
        for origin,dest,hub,first,last,wait in [
            ('BLV','SFB','JAX',1218,1437,240),('MKE','SFB','MCI',1264,1036,240),
            ('PGD','CAK','MCI',1197,2017,240),('DAL','PNS','MCI',1045,2019,240),
            ('VPS','BWI','JAX',1727,1088,240),('RDU','SGF','MCI',1138,1723,240),
            ('PIT','BHM','DAY',2193,1981,158),('MCI','PIT','DAY',1537,2194,55),
            ('PIT','GRR','DAY',2193,1809,160)]:
            with self.subTest(market=f'{origin}-{dest}'):
                audit=audit_hub_connections(CANONICAL,hub=hub,groups={'source':[origin],'destination':[dest]})
                pair=next(p for p in audit['directionalPairs'] if p['source']==origin)
                self.assertEqual(pair['status'],'connected')
                self.assertTrue(any((p['inboundFlight'],p['outboundFlight'],p['waitMinutes'])==(first,last,wait) for p in pair['options']))

if __name__=='__main__':unittest.main()
