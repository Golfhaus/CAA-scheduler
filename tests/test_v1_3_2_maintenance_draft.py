"""The maintenance repair must preserve flying and make every repeat eligible."""
import json,sys,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
class MaintenanceRepairTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base=json.loads((ROOT/'data/schedules/schedule_7_v1_3_1/canonical_schedule.json').read_text())
  cls.now=json.loads((ROOT/'data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json').read_text())
  cls.report=validate_operating_rules(cls.now)
 def test_repeating_lines_have_real_eligible_overnights(self):
  targets=set(self.now['operatingPolicy']['ronTargetCities'])
  for line in {l['line']for l in self.now['legs']}:
   ls=[l for l in self.now['legs']if l['line']==line];ends=[max((l for l in ls if l['day']==d),key=lambda l:l['sequenceWithinRoute'])for d in {l['day']for l in ls}]
   self.assertTrue(any(l['destination']in targets for l in ends),line)
  self.assertEqual(self.report['summary']['effectiveErrorFindings'],0)
  grace=next(c for c in self.report['checks']if c['id']=='rolling_ron_grace')
  self.assertEqual([f['id']for f in grace['findings']],['AM'])
  self.assertEqual(grace['findings'][0]['evidence']['longestRunWithoutTargetRon'],11)
 def test_only_approved_flying_changes_and_no_extra_inventory(self):
  old={l['id']:l for l in self.base['legs']};now={l['id']:l for l in self.now['legs']};self.assertEqual(len(old)+2,len(now))
  self.assertEqual({old[i]['flight']for i in old.keys()-now.keys()},{1257,1258})
  self.assertEqual({now[i]['flight']for i in now.keys()-old.keys()},{2217,2218,2219,2220})
  for i in old.keys()&now.keys():self.assertEqual(tuple(old[i][k]for k in ['flight','fleet','pairing','origin','destination']),tuple(now[i][k]for k in ['flight','fleet','pairing','origin','destination']))
  changes={old[i]['flight']:now[i]['departureMinute']-old[i]['departureMinute']for i in old.keys()&now.keys()if now[i]['departureMinute']!=old[i]['departureMinute']}
  self.assertEqual(changes,{1817:1,1904:43,1256:-165,1219:-165,1892:-8,1699:-10})
  for key in ['cities','hubBanks','operatingPolicy']:self.assertEqual(self.now[key],self.base[key])
  self.assertEqual(self.now['schedule']['fleetCounts'],self.base['schedule']['fleetCounts'])
 def test_accepted_r501_has_no_long_same_day_hold(self):
  ls=sorted([l for l in self.now['legs']if l['route']==501],key=lambda l:l['sequenceWithinRoute'])
  self.assertEqual([(l['origin'],l['destination'])for l in ls],[('ABE','MYR'),('MYR','ABE'),('ABE','SFB'),('SFB','RFD'),('RFD','SFB'),('SFB','SAT')])
  self.assertEqual(max(b['departureMinute']-a['arrivalMinute']for a,b in zip(ls,ls[1:])),147)
 def test_rotation_size_and_physical_checks(self):
  for line in ['AL','AK']:self.assertEqual(len({l['day']for l in self.now['legs']if l['line']==line}),12)
  self.assertFalse(any(l['line']in{'AO','AQ'}for l in self.now['legs']))
  self.assertEqual(validate_overnight_turns(self.now)['status'],'pass')
  export_gate_schedule(self.now)
  self.assertFalse(any(c['hardStop']and c['status']=='fail'for c in self.report['checks']))
 def test_accepted_r175_turn_and_unchanged_afternoon(self):
  ls=sorted([l for l in self.now['legs']if l['route']==175],key=lambda l:l['sequenceWithinRoute'])
  self.assertEqual(len(ls),8)
  self.assertEqual([(l['flight'],l['departure'],l['arrival'])for l in ls[:4]],[(1892,'06:47','07:45'),(1699,'08:25','09:33'),(2219,'10:13','11:43'),(2220,'12:23','13:53')])
  self.assertEqual(max(b['departureMinute']-a['arrivalMinute']for a,b in zip(ls,ls[1:])),86)
  old={l['flight']:l for l in self.base['legs']}
  for l in ls[4:]:self.assertEqual((l['departure'],l['arrival']),(old[l['flight']]['departure'],old[l['flight']]['arrival']))
if __name__=='__main__':unittest.main()
