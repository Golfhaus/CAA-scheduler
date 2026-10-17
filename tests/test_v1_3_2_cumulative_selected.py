"""Protect the full unpublished v1.3.2 canonical after the pinned five-round tests."""
from pathlib import Path
import json,unittest,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
class CumulativeSelectedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.now=json.loads((ROOT/'data/schedules/schedule_7_v1_3_2_draft/canonical_schedule.json').read_text())
  cls.pinned=json.loads((ROOT/'outputs/schedule_7_v1_3_2_group_selected/canonical_schedule.json').read_text())
 def test_reproduces_validated_working_draft(self):
  self.assertEqual(len(self.now['legs']),1229)
  self.assertEqual(self.now['legs'],self.pinned['legs'])
  self.assertEqual(self.now['bankAssignments'],self.pinned['bankAssignments'])
  self.assertEqual(self.now['hubBanks'],self.pinned['hubBanks'])
  self.assertEqual(self.now['schedule'],self.pinned['schedule'])
  overlays=self.now['provenance']['workingDraft']['draftOverlays']
  self.assertEqual(len(overlays),9)
  self.assertTrue(overlays[-1]['path'].endswith('r158_selected.json'))
 def test_selected_routes_and_unchanged_targets(self):
  flights={l['flight']:l for l in self.now['legs']}
  for f in [2227,2228,2229,2230,2231,2232,2233,2234,2235,2236]:
   self.assertIn(f,flights)
  for f in [2053,2054]:
   self.assertNotIn(f,flights)
  expected={144:8,146:7,158:7,176:8,107:6,125:9,160:6}
  for route,count in expected.items():
   self.assertEqual(len([l for l in self.now['legs'] if l['route']==route]),count)
 def test_native_gate_and_rotation(self):
  self.assertEqual(validate_schedule(self.now)['status'],'pass')
  self.assertEqual(validate_overnight_turns(self.now)['status'],'pass')
  op=validate_operating_rules(self.now)
  self.assertEqual(op['summary']['effectiveErrorFindings'],0)
  gates=export_gate_schedule(self.now)
  stands=[x for city in gates['cities'] for x in city['claims'] if x['rowType']=='stand']
  self.assertEqual((len(stands),sum(x['end']-x['start'] for x in stands)),(15,3061))
if __name__=='__main__':unittest.main()
