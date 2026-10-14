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
 def test_no_flying_inventory_or_policy_is_added(self):
  old={l['id']:l for l in self.base['legs']};now={l['id']:l for l in self.now['legs']};self.assertEqual(old.keys(),now.keys())
  for i,l in old.items():self.assertEqual(tuple(l[k]for k in ['flight','fleet','pairing','origin','destination']),tuple(now[i][k]for k in ['flight','fleet','pairing','origin','destination']))
  changes={l['flight']:now[i]['departureMinute']-l['departureMinute']for i,l in old.items()if now[i]['departureMinute']!=l['departureMinute']}
  self.assertEqual(changes,{1817:1,1904:43})
  for key in ['cities','hubBanks','operatingPolicy']:self.assertEqual(self.now[key],self.base[key])
  self.assertEqual(self.now['schedule']['fleetCounts'],self.base['schedule']['fleetCounts'])
 def test_rotation_size_and_physical_checks(self):
  for line in ['AL','AK']:self.assertEqual(len({l['day']for l in self.now['legs']if l['line']==line}),12)
  self.assertFalse(any(l['line']in{'AO','AQ'}for l in self.now['legs']))
  self.assertEqual(validate_overnight_turns(self.now)['status'],'pass')
  export_gate_schedule(self.now)
  self.assertFalse(any(c['hardStop']and c['status']=='fail'for c in self.report['checks']))
if __name__=='__main__':unittest.main()
