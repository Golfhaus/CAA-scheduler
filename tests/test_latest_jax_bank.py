"""Latest release: accepted flying, preserved limits and priority connections."""
import hashlib,json
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from latest_schedule import CANONICAL,SCHEDULE_ID,RELEASE_CONFIG
from caa_scheduler.optimization_release import audit_hub_connections
from caa_scheduler.optimization_overlay import apply_optimization_overlay
class LatestApprovedFlyingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base=json.loads((ROOT/'data/schedules/schedule_7_v1_3_0/canonical_schedule.json').read_text())
  cls.overlay=json.loads((ROOT/'config/optimizations/schedule_7_v1_3_1_release_overlay.json').read_text())
 def test_release_matches_the_accepted_draft_and_new_flying(self):
  self.assertEqual(SCHEDULE_ID,'schedule_7_v1_3_1')
  config=json.loads(RELEASE_CONFIG.read_text());source=ROOT/'data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json'
  self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),config['connectionScopeDecision']['acceptedDraftSha256'])
  self.assertEqual(CANONICAL['legs'],json.loads(source.read_text())['legs'])
  added=[l for l in CANONICAL['legs']if l['id']not in {x['id']for x in self.base['legs']}]
  self.assertEqual([l['flight']for l in added],list(range(2195,2217)))
  by={l['flight']:l for l in CANONICAL['legs']}
  expected={2195:('RFD','JAX','05:40','08:56'),2196:('JAX','RFD','09:40','10:56'),2197:('RFD','JAX','12:14','15:30'),2198:('JAX','RFD','16:10','17:26'),2199:('RFD','MCI','19:26','20:40'),2200:('MCI','RFD','21:20','22:34'),2201:('PGD','SYR','04:46','07:45'),2204:('SYR','DAB','16:41','19:19'),2207:('DAB','SYR','05:07','07:45'),2210:('SYR','PGD','13:55','16:54'),2215:('MCI','DSM','14:00','14:50'),2216:('DSM','MCI','15:35','16:25')}
  for f,row in expected.items():self.assertEqual(tuple(by[f][k]for k in ['origin','destination','departure','arrival']),row)
  self.assertEqual((by[1210]['departure'],by[1209]['departure']),('07:15','08:55'))
 def test_only_approved_retimings_and_route_changes_are_released(self):
  projected=apply_optimization_overlay(self.base,self.overlay)
  self.assertEqual(CANONICAL['legs'],projected['legs'])
  after={l['id']:l for l in CANONICAL['legs']};changed=[l for l in self.base['legs']if (l['departureMinute'],l['arrivalMinute'])!=(after[l['id']]['departureMinute'],after[l['id']]['arrivalMinute'])]
  self.assertEqual(len(changed),15)
  for l in self.base['legs']:
   self.assertEqual(tuple(l[k]for k in ['id','flight','pairing','origin','destination','fleet']),tuple(after[l['id']][k]for k in ['id','flight','pairing','origin','destination','fleet']))
  self.assertEqual(CANONICAL['schedule']['fleetCounts'],self.base['schedule']['fleetCounts'])
  self.assertEqual([l for l in CANONICAL['legs']if l['route']==150],[l for l in self.base['legs']if l['route']==150])
 def test_banks_and_physical_inventory_are_preserved(self):
  self.assertEqual(CANONICAL['cities'],self.base['cities']);self.assertEqual(CANONICAL['hubBanks'],self.base['hubBanks'])
  self.assertEqual({k:v for k,v in CANONICAL['gatePlan'].items()if k!='label'},{k:v for k,v in self.base['gatePlan'].items()if k!='label'})
  self.assertEqual(CANONICAL['schedule']['connectionWindowMinutes'],self.base['schedule']['connectionWindowMinutes'])
  self.assertEqual(CANONICAL['operatingPolicy'],apply_optimization_overlay(self.base,self.overlay)['operatingPolicy'])
 def test_priority_two_way_connections_and_preserved_r307_service(self):
  for hub,groups in [('SYR',{'northeast':['HPN','HVN','ISP','BTV','ORH'],'Florida':['PGD','DAB','FLL','PIE','SFB','SRQ']}),('JAX',{'RFD':['RFD'],'priorities':['MYR','EYW','ECP','ILM','ROA','TLH']})]:
   audit=audit_hub_connections(CANONICAL,hub=hub,groups=groups)
   self.assertTrue(all(p['status']=='connected'for p in audit['directionalPairs']))
  a=audit_hub_connections(CANONICAL,hub='DAY',groups={'PIT':['PIT'],'BHM':['BHM']})
  outbound=next(p for p in a['directionalPairs']if p['source']=='PIT')
  self.assertTrue(any((p['inboundFlight'],p['outboundFlight'],p['waitMinutes'])==(2193,1981,158)for p in outbound['options']))
if __name__=='__main__':unittest.main()
