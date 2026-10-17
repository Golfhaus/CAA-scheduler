"""Reproducibility regression for unpublished v1.3.3 BHM mini-banks."""
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
class MiniBanks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=json.loads((ROOT/"data/schedules/schedule_7_v1_3_2/canonical_schedule.json").read_text())
  cls.current=json.loads((ROOT/"data/schedules/schedule_7_v1_3_3_draft/canonical_schedule.json").read_text())
  cls.screen=json.loads((ROOT/"outputs/schedule_7_v1_3_3_bhm_minibanks_mx5/day_day_canonical.json").read_text())
  cls.audit=json.loads((ROOT/"outputs/schedule_7_v1_3_3_bhm_minibanks_mx5/network_screen.json").read_text())
 def test_draft_and_checkpoint_scope(self):
  c=self.current
  self.assertEqual(c["schedule"]["id"],"schedule_7_v1_3_3_draft")
  self.assertEqual(c["schedule"]["status"],"draft")
  self.assertEqual(len(c["legs"]),1253)
  self.assertEqual(len({l["route"] for l in c["legs"]}),188)
  self.assertEqual(len({l["line"] for l in c["legs"]}),21)
  self.assertEqual(c["schedule"]["fleetCounts"],self.before["schedule"]["fleetCounts"])
  self.assertEqual(c["cities"],self.before["cities"])
  self.assertEqual(c["hubBanks"],self.before["hubBanks"])
  manifest=json.loads((ROOT/"web/schedules.json").read_text())
  self.assertEqual(manifest["defaultScheduleId"],"schedule_7_v1_3_2")
  self.assertEqual(c["provenance"]["workingDraft"]["revertPoint"]["commit"],"6965d28175b4089c269f543a1d6b24b423fbdcb3")
 def test_screened_flying_is_identical(self):
  self.assertEqual(self.current["legs"],self.screen["legs"])
  self.assertEqual(self.current["bankAssignments"],self.screen["bankAssignments"])
  self.assertEqual(self.current["operatingPolicy"],self.screen["operatingPolicy"])
  added=[x for x in self.current["legs"] if x["route"] in {529,530,357,358}]
  self.assertEqual(len(added),24)
  self.assertEqual({k:len([x for x in added if x["route"]==k]) for k in (529,530,357,358)},
    {529:6,530:6,357:6,358:6})
 def test_physical_capacity_and_maintenance(self):
  c=self.current
  self.assertEqual(validate_schedule(c)["status"],"pass")
  v=validate_operating_rules(c)
  self.assertEqual(v["summary"]["effectiveErrorFindings"],0)
  self.assertEqual(validate_overnight_turns(c)["status"],"pass")
  self.assertEqual(validate_planning_snapshot(reconstruct_planning_snapshot(c),c)["status"],"pass")
  gates=export_gate_schedule(c)
  bhm=next(x for x in gates["cities"] if x["code"]=="BHM")
  self.assertEqual((bhm["nGates"],bhm["nStands"]),(6,4))
  fleet=next(x for x in v["checks"] if x["id"]=="fleet_capacity")["metrics"]
  self.assertEqual((fleet["CRJ900"]["used"],fleet["CRJ700"]["used"]),(30,58))
  self.assertEqual((fleet["CRJ900"]["capacity"],fleet["CRJ700"]["capacity"]),(45,65))
 def test_geographic_connections_and_no_losses(self):
  s=self.audit["summary"]
  self.assertEqual((s["coverageGains"],s["coverageLosses"]),(60,0))
  self.assertEqual((s["faster"],s["slower"]),(117,0))
  self.assertEqual((s["northToSouthServed"],s["southToNorthServed"]),(15,13))
  self.assertIn("CAK-PGD",s["newlyOneStop"])
if __name__=="__main__":unittest.main()
