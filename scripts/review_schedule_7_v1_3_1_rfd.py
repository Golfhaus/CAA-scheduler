"""Reproduce the JAX/BHM feeder and existing MAX9 idle screen for the draft."""
import csv,json,collections,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.bank_placement import _block_minutes
config=json.loads((ROOT/'config/optimizations/schedule_7_v1_3_1_round_1.json').read_text())
source=ROOT/config['baseSchedule']['canonical'];assert hashlib.sha256(source.read_bytes()).hexdigest()==config['baseSchedule']['sha256']
b=json.loads(source.read_text());cs={c['code']:c for c in b['cities']};p=json.loads((ROOT/'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles'][0]
odpath=ROOT/'data/reference/airport_od_matrix_consolidated_v2.csv';assert hashlib.sha256(odpath.read_bytes()).hexdigest()=='49c04922ee0cebb3fef8aad923e04bd11874587a263c9511358ddb833b860bc6'
rows=list(csv.reader(odpath.read_text().splitlines()));h=next(i for i,x in enumerate(rows) if x and x[0]=='Origin \\ Dest');codes=rows[h][1:];od={x[0]:dict(zip(codes,[float(v or 0) for v in x[1:]])) for x in rows[h+1:] if x}
priority=['MYR','EYW','ECP','ILM','ROA','TLH']
report={'status':'draft analysis; publication not authorized','baseScheduleId':b['schedule']['id'],'baseCanonicalSha256':config['baseSchedule']['sha256'],'hubs':{},'existingMax9IdleScreen':[],'timingBuffers':'TLH morning inbound and ECP/TLH evening outbound connections have 235-minute waits, five minutes inside the 240-minute maximum.','geographicCaveat':'ROA–RFD via JAX has distance ratio 2.35649 and is excluded by the unchanged 2.25 opportunity screen, although the timetable accepts both connections.'}
for hub in ['JAX','BHM']:
 feed={code:{'cityToRfdOd':od[code]['RFD'],'rfdToCityOd':od['RFD'][code],'intoHub':[l['flight'] for l in b['legs'] if l['origin']==code and l['destination']==hub],'fromHub':[l['flight'] for l in b['legs'] if l['origin']==hub and l['destination']==code]} for code in priority}
 report['hubs'][hub]={'blockMinutes':_block_minutes(hub,'RFD',p,cs),'hubToRfdOd':od[hub]['RFD'],'rfdToHubOd':od['RFD'][hub],'feeders':feed,'missingTwoWayFeeders':[code for code,r in feed.items() if not r['intoHub'] or not r['fromHub']]}
by=collections.defaultdict(list)
for l in b['legs']:by[l['route']].append(l)
for route,ls in by.items():
 if ls[0]['fleet']!='MAX9':continue
 ls.sort(key=lambda l:l['sequenceWithinRoute'])
 for i,a in enumerate(ls):
  if i==0 and a['origin'] in ['JAX','BHM','RFD']:report['existingMax9IdleScreen'].append({'route':route,'kind':'before originator','station':a['origin'],'minutesAfter0430':max(0,a['departureMinute']-270),'flight':a['flight']})
  if i+1<len(ls) and a['destination'] in ['JAX','BHM','RFD']:report['existingMax9IdleScreen'].append({'route':route,'kind':'same-day hold','station':a['destination'],'minutes':(ls[i+1]['departureMinute']-a['arrivalMinute'])%1440,'afterFlight':a['flight'],'beforeFlight':ls[i+1]['flight']})
  if i==len(ls)-1 and a['destination'] in ['JAX','BHM','RFD']:report['existingMax9IdleScreen'].append({'route':route,'kind':'after terminator','station':a['destination'],'minutesUntilLatestDeparture':max(0,(1410 if a['destination'] in ['JAX','BHM'] else 1260)-a['arrivalMinute']),'flight':a['flight']})
report['minimumSameDayInsertionMinutes']={'JAX':2*136+3*40,'BHM':2*103+3*40,'RFD_to_JAX':2*136+3*40,'RFD_to_BHM':2*103+3*40}
singles=[]
for minute in range(270,1411):
 if not any(x['hub']=='JAX' and x['startMinute']<=minute<x['endMinute'] for x in b['hubBanks']):continue
 covered=[code for code in priority if any(l['origin']==code and l['destination']=='JAX' and 30<=(minute-l['arrivalMinute'])%1440<=240 for l in b['legs'])]
 singles.append({'departureMinute':minute,'covered':covered})
report['maximumPriorityCitiesFedBySingleJaxDeparture']=max(len(x['covered']) for x in singles)
assert report['maximumPriorityCitiesFedBySingleJaxDeparture']<6
report['selectedOutboundCoverage']=[x for x in singles if x['departureMinute'] in [580,970]]
assert set().union(*(set(x['covered']) for x in report['selectedOutboundCoverage']))==set(priority)
report['singleRoundTripConstraint']='No bank-valid JAX departure can receive all six unchanged feeders; the maximum is four. Two departures receive all six, using one new four-leg MAX9 aircraft-day.'
out=ROOT/'outputs/schedule_7_v1_3_1';out.mkdir(parents=True,exist_ok=True);(out/'corridor_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'singleDepartureMaximumPriorityCities':report['maximumPriorityCitiesFedBySingleJaxDeparture'],'selectedOutboundCoverage':report['selectedOutboundCoverage'],'BhmMissingFeeders':report['hubs']['BHM']['missingTwoWayFeeders']}))
