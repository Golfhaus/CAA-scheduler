"""Validate evening alternatives without modifying the accepted v1.3.1 draft."""
from pathlib import Path
import sys,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
active_source=ROOT/'data/schedules/schedule_7_v1_3_1_draft/canonical_schedule.json';active_raw=active_source.read_bytes()
subprocess.run([sys.executable,str(ROOT/'scripts/build_schedule_7_v1_3_1_draft.py'),'--round-1'],check=True)
source=ROOT/'outputs/schedule_7_v1_3_1_evening/base_four_leg_canonical.json';raw=source.read_bytes();base=json.loads(raw);output=ROOT/'outputs/schedule_7_v1_3_1_evening';output.mkdir(parents=True,exist_ok=True)
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
results={}
for name in ['mci','day','bhm','phf']:
 config=ROOT/f'config/proposals/schedule_7_v1_3_1_evening_{name}.json';overlay=json.loads(config.read_text());assert hashlib.sha256(raw).hexdigest()==overlay['baseSchedule']['sha256']
 c=apply_optimization_overlay(base,overlay);structure=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c);planning=validate_planning_snapshot(reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7'),c);gates=export_gate_schedule(c)
 original={l['id']:l for l in base['legs']};changed={l['legId'] for l in overlay.get('retimeLegs',[])}
 for l in c['legs']:
  if l['id'] in original:
   allowed={'sequenceWithinRoute'}|({'departure','arrival','departureMinute','arrivalMinute'} if l['id'] in changed else set());assert all(l[k]==v for k,v in original[l['id']].items() if k not in allowed)
 assert c['operatingPolicy']==base['operatingPolicy'] and c['hubBanks']==base['hubBanks'] and c['cities']==base['cities'] and c['schedule']['fleetCounts']==base['schedule']['fleetCounts']
 assert structure['status']=='pass' and operating['summary']['effectiveErrorFindings']==0 and overnight['status']=='pass' and planning['status']=='pass'
 stands=[s for city in gates['cities'] for s in city['claims'] if s['rowType']=='stand']
 results[name]={'valid':True,'structural':structure['summary'],'operating':operating['summary'],'overnightStatus':overnight['status'],'planningStatus':planning['status'],'standUse':{'claims':len(stands),'minutes':sum(s['end']-s['start'] for s in stands)},'newFlights':[l for l in c['legs'] if l['id'] not in original],'retimedFlights':[l['flight'] for l in c['legs'] if l['id'] in changed],'overlaySha256':hashlib.sha256(config.read_bytes()).hexdigest(),'canonicalSha256':hashlib.sha256((json.dumps(c,indent=2)+'\n').encode()).hexdigest()}
 write(output/f'{name}_canonical.json',c)
 print(name,json.dumps({'valid':True,'standUse':results[name]['standUse'],'retimedFlights':results[name]['retimedFlights']}),flush=True)
write(output/'native_review.json',{'status':'Historical four-leg evening comparison; MCI accepted via round 2, others not implemented','baseSha256':hashlib.sha256(raw).hexdigest(),'alternatives':results});assert source.read_bytes()==raw and active_source.read_bytes()==active_raw
