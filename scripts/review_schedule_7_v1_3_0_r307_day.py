"""Review PIT-DAY-PIT alternatives; preserve the accepted v1.3.0 draft."""
from pathlib import Path
import hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.bank_placement import _block_minutes
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.planning import reconstruct_planning_snapshot,validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule

source=ROOT/'data/schedules/schedule_7_v1_3_0_draft/canonical_schedule.json'
raw=source.read_bytes();base=json.loads(raw)
cities={c['code']:c for c in base['cities']}
profile=next(p for p in json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles'] if p['fleet']=='CRJ700')
block=_block_minutes('PIT','DAY',profile,cities)
assert block==57
before=next(l for l in base['legs'] if l['flight']==1917)
following=next(l for l in base['legs'] if l['flight']==1918)
outdir=ROOT/'outputs/schedule_7_v1_3_0_r307_day';outdir.mkdir(parents=True,exist_ok=True)
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def bank(minute):return next((b['id'] for b in base['hubBanks'] if b['hub']=='DAY' and b['startMinute']<=minute<b['endMinute']),None)
candidates=[]
for departure in range(before['arrivalMinute']+40,following['departureMinute']-40-2*block-40+1):
 arrival=departure+block
 if not bank(arrival):continue
 for back in range(arrival+40,following['departureMinute']-40-block+1):
  if not bank(back):continue
  candidates.append({'departure':departure,'arrival':arrival,'back':back,'returnArrival':back+block,'arrivalBank':bank(arrival),'departureBank':bank(back),'groundMinutes':[departure-before['arrivalMinute'],back-arrival,following['departureMinute']-back-block]})
assert len(candidates)==210
report={'baseSha256':hashlib.sha256(raw).hexdigest(),'status':'analysis only; not accepted','blockMinutes':block,'holdMinutes':following['departureMinute']-before['arrivalMinute'],'candidates':candidates,'validated':{}}
write(outdir/'screen.json',report)
if '--validate' in sys.argv:
 ranking=json.loads((outdir/'connection_review.json').read_text())
 assert ranking['baseSha256']==report['baseSha256']
 for name,t in ranking['selected'].items():
  additions=[{'id':'V130-R307-PIT-DAY','route':307,'origin':'PIT','destination':'DAY','departureMinute':t['departure'],'arrivalMinute':t['arrival']},{'id':'V130-R307-DAY-PIT','route':307,'origin':'DAY','destination':'PIT','departureMinute':t['back'],'arrivalMinute':t['returnArrival']}]
  overlay={'schemaVersion':'1.0.0','id':'schedule-7-v1.3.0-proposed-r307-day-'+name,'baseSchedule':{'scheduleId':base['schedule']['id'],'canonical':source.relative_to(ROOT).as_posix(),'sha256':report['baseSha256']},'schedule':{'id':'schedule_7_v1_3_0_proposal_r307_day_'+name,'version':'1.3.0-analysis','label':'R307 DAY round trip '+name+'; unpublished proposal','status':'draft'},'approval':{'status':'analysis only; user asked for review','publication':'Not authorized'},'insertLegs':additions,'bankAssignmentsToAdd':[{'legId':additions[0]['id'],'operation':'arrival','bankId':t['arrivalBank']},{'legId':additions[1]['id'],'operation':'departure','bankId':t['departureBank']}]}
  c=apply_optimization_overlay(base,overlay)
  old={l['id']:l for l in base['legs']}
  for l in c['legs']:
   if l['id'] in old:assert all(v==l[k] for k,v in old[l['id']].items() if k!='sequenceWithinRoute')
  assert c['operatingPolicy']==base['operatingPolicy'] and c['hubBanks']==base['hubBanks']
  structural=validate_schedule(c);operating=validate_operating_rules(c);overnight=validate_overnight_turns(c)
  planning=validate_planning_snapshot(reconstruct_planning_snapshot(c,demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7'),c)
  gates=export_gate_schedule(c)
  valid=structural['status']=='pass' and operating['summary']['effectiveErrorFindings']==0 and not any(x['hardStop'] and x['status']=='fail' for x in operating['checks']) and overnight['status']=='pass' and planning['status']=='pass'
  stands=[s for city in gates['cities'] for s in city['claims'] if s['rowType']=='stand']
  report['validated'][name]={'valid':valid,'timing':t,'newFlights':[l for l in c['legs'] if l['id'] not in old],'structural':structural['summary'],'operating':operating['summary'],'overnightStatus':overnight['status'],'planningStatus':planning['status'],'standClaims':len(stands),'standMinutes':sum(s['end']-s['start'] for s in stands),'stations':[{k:city[k] for k in ['code','nGates','nStands','peakUsed']} for city in gates['cities'] if city['code'] in ['PIT','DAY']]}
  write(ROOT/f'config/proposals/schedule_7_v1_3_0_r307_day_{name}.json',overlay)
  write(outdir/f'{name}_canonical.json',c)
  print(name,valid,t['groundMinutes'],operating['summary'])
 write(outdir/'validation_review.json',report)
assert source.read_bytes()==raw,'Review changed the accepted draft'
print('Screened',len(candidates),'timings without changing existing flights')
