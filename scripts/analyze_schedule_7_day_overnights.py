"""Review DAY destination RONs on aligned routes 125/136; never implement or publish.

Replay the pinned alignment first. Test the seven short-listed portfolios with
isolated first-flight shifts, full gate/turn/MX checks and connection audits.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,validate,retime,demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_4 import cache_network
from caa_scheduler.io import read_json,write_json,sha256_file
from review_crj200_line_alignment import main as replay_alignment
replay_alignment()
alignment='config/optimizations/schedule_7_crj200_line_alignment.json'
base=ROOT/'builds/crj200-line-alignment/canonical_schedule.json';b=read_json(base);s=HoldSearch(b);cache_network(s)
report={'status':'review only; new flying not implemented','baseCanonical':str(base.relative_to(ROOT)), 'baseSha256':sha256_file(base),'alignmentOverlay':alignment,'alignmentOverlaySha256':sha256_file(ROOT/alignment),'model':'Pinned BTS O-D; full-capture seat-uncapped relative-choice one/two-stop opportunity units, not forecast passengers, loads or profit. 30–240 minute transfers and circuity ≤2.25.', 'recommendedCandidate':'IND_CAK','candidates':[]}
for tag,a,da,bb,db in [('IND_CMH','IND',3,'CMH',0),('LEX_IND','LEX',6,'IND',3),('LEX_CMH','LEX',6,'CMH',0),('CMH_IND','CMH',0,'IND',3),('IND_CAK','IND',3,'CAK',10),('CMH_CAK','CMH',0,'CAK',10),('LEX_CAK','LEX',6,'CAK',10)]:
 added=[{'route':125,'legs':[s.leg('DAY',a,1295,'CRJ200')]},{'route':126,'legs':[s.leg(a,'DAY',270,'CRJ200')]},{'route':136,'legs':[s.leg('DAY',bb,1295,'CRJ200')]},{'route':137,'legs':[s.leg(bb,'DAY',270,'CRJ200')]}]
 changes=retime(s,126,[da])+retime(s,137,[db]);c=make_overlay(s,added,retimings=changes)
 c['baseSchedule'].update(canonical=str(base.relative_to(ROOT)),sha256=sha256_file(base));c['id']='day-overnight-'+tag;c['schedule'].update(id='schedule_7_day_overnight_'+tag,label='Unpublished DAY overnight candidate '+tag,version='1.2.4-day-overnight')
 for old,new in [(l['id'],l['id'].replace('V123-',f'DAY-RON-{tag}-')) for l in c['insertLegs']]:
  next(l for l in c['insertLegs'] if l['id']==old)['id']=new
  for x in c['bankAssignmentsToAdd']:
   if x['legId']==old:x['legId']=new
 if 'CAK' in (a,bb):
  c['hubBankChanges']=[{'bankId':'DAY-B1','expectedStartMinute':300,'expectedEndMinute':360,'startMinute':301,'endMinute':361}]
 c['baseSchedule'].update(alignmentOverlay=alignment,alignmentOverlaySha256=sha256_file(ROOT/alignment))
 c['approval']={'status':'reviewed proposal; not implemented','publication':'Reserved to user decision'}
 v,t=validate(s,c);q={'id':tag,'destinations':[a,bb],'originatorDelays':[da,db],'validation':v,'hubBankChanges':c.get('hubBankChanges',[])}
 print('VALIDATE',tag,v['operatingErrors'],v['gates'],v['blocking'],flush=True)
 if not v['operatingErrors'] and v['gates']=='pass':
  q['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});q['audit']=audit(s,t)
  q['addedFlyingOpportunityUnits']=sum(l['total'] for l in q['demand']['flights'])
  q['earlyReturnConnections']={}
  options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
  q['changedFlights']=[]
  allowed_changes={z['legId'] for z in changes};original={l['id']:l for l in b['legs']};actual={l['id']:l for l in t['legs']}
  assert all({k:v for k,v in actual[i].items() if k!='sequenceWithinRoute'}=={k:v for k,v in l.items() if k!='sequenceWithinRoute'} for i,l in original.items() if i not in allowed_changes)
  assert len(actual)==1174
  from analyze_schedule_7_v1_2_4_xna import maintenance
  q['maintenance']={line:maintenance(t,line) for line in ('AE','AF')}
  assert all(z['maximumConsecutiveNonTargetRons']<=10 for z in q['maintenance'].values())
  for ch in changes:
   old=s.legs[ch['legId']];before={tuple(z['legs']) for z in s.screen.connections[old['id']]};after={tuple(z['legs']) for z in records[old['id']]}
   q['changedFlights'].append({'flight':old['flight'],'beforeDeparture':old['departure'],'afterDeparture':next(l['departure'] for l in t['legs'] if l['id']==old['id']),'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before),'oldOpportunity':sum(s.screen.loads[old['id']].values()),'newOpportunity':sum(loads[old['id']].values())})
  q['connections']={}
  for l in t['legs']:
   if l['id'] not in {x['id'] for x in c['insertLegs']}:continue
   if l['destination']=='DAY':
    later=[]
    for d in t['legs']:
     if d['origin']=='DAY' and 30<=(d['departureMinute']-l['arrivalMinute'])%1440<=240:later.append({k:d[k] for k in ['flight','destination','departure','departureMinute']})
    q['connections'][str(l['flight'])]=sorted(later,key=lambda x:x['departureMinute'])
  write_json(ROOT/f'config/proposals/schedule_7_day_overnight_{tag.lower()}.json',c);write_json(ROOT/f'builds/day-overnight-review/{tag}-canonical.json',t)
  print('DEMAND',tag,[(l['origin']+'-'+l['destination'],round(l['total'],1),round(l['local'],1),round(l['oneStop'],1),round(l['twoStop'],1)) for l in q['demand']['flights']],'LOST',len(q['audit']['marketsLosingAllConnections']),'SLOWER',len(q['audit']['marketsWithSlowerBestItinerary']),'CH',q['changedFlights'],flush=True)
 report['candidates'].append(q);write_json(ROOT/'config/proposals/schedule_7_day_overnight_review.json',report)

report['screen']=read_json(ROOT/'config/proposals/schedule_7_day_overnight_screen.json')
assert report['screen']['baseSha256']==sha256_file(base), 'Stale nearby screen'
# Keep decision statistics and exact flight references; verbose gate/canonical
# data is reproducible in builds rather than duplicated in the review.
for q in report['candidates']:
 q['validation'].pop('affectedStations',None)
 for detail in q.get('maintenance',{}).values():detail.pop('longestRun',None)
 for f in q.get('demand',{}).get('flights',[]):
  refs=f.pop('connectingFlights',[])
  f['connectingFlightCount']=len(refs);f['connectingFlightNumbers']=[x['flight'] for x in refs]
  f['topMarkets']=f['topMarkets'][:5]
for destination in report['screen']['destinations']:
 by_route={}
 for timing in destination['timings']:by_route.setdefault(timing['route'],timing)
 destination['timings']=list(by_route.values())
write_json(ROOT/'config/proposals/schedule_7_day_overnight_review.json',report)
