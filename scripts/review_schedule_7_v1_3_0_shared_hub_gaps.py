"""Read-only screening and validation of shared-hub bidirectional gaps."""
from pathlib import Path
import copy,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from caa_scheduler.operating_validation import validate_operating_rules,validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.optimization_overlay import apply_optimization_overlay
BASE=ROOT/'data/schedules/schedule_7_v1_3_0_draft/canonical_schedule.json'
base=json.loads(BASE.read_text());hubs=set(base['operatingPolicy']['hubs']+base['operatingPolicy']['focusCities'])
pairs=[('CAK','PGD'),('BLV','HOU'),('MYR','RFD'),('BNA','OMA')]
rows=[]
for a,b in pairs:
 for origin,destination in ((a,b),(b,a)):
  choices=[]
  for first in base['legs']:
   if first['origin']!=origin or first['destination']not in hubs:continue
   for second in base['legs']:
    if second['origin']!=first['destination'] or second['destination']!=destination:continue
    wait=(second['departureMinute']-first['arrivalMinute'])%1440
    shift=min((30-wait,240-wait,1470-wait),key=abs)
    choices.append({'origin':origin,'destination':destination,'hub':first['destination'],'firstFlight':first['flight'],'firstRoute':first['route'],'arrival':first['arrival'],'secondFlight':second['flight'],'secondRoute':second['route'],'departure':second['departure'],'waitMinutes':wait,'outboundClockShiftMinutes':shift,'minimumTotalClockAdjustment':abs(shift)})
  choices.sort(key=lambda x:abs(x['outboundClockShiftMinutes']))
  rows.append({'origin':origin,'destination':destination,'closest':choices[:6]})
OUT=ROOT/'outputs/schedule_7_v1_3_0_shared_hub_gaps';OUT.mkdir(parents=True,exist_ok=True)
CASES={'pgd_cak_2':{2017:-2},'blv_hou_6':{1357:6},'oma_bna_11':{1077:-11},'bna_oma_both':{1077:-11,1080:-89},'rfd_myr_2_flights':{1660:-101,1714:-81},'myr_rfd_both_new_bank':{1713:79,1660:-101,1714:-81}}
report={'baseCanonical':BASE.relative_to(ROOT).as_posix(),'baseSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'status':'Proposals only; accepted draft is unchanged','screen':rows,'cases':{}}
for name,changes in CASES.items():
 c=copy.deepcopy(base);reassigned=[];new_banks=[]
 if name=='myr_rfd_both_new_bank':
  bank={'id':'PHF-V130-PROPOSED-MORNING','hub':'PHF','startMinute':435,'endMinute':495};c['hubBanks'].append(bank);c['operatingPolicy']['hubBankCounts']['PHF']+=1;new_banks.append(bank)
 for l in c['legs']:
  if l['flight']not in changes:continue
  d=changes[l['flight']]
  for key in ('departureMinute','arrivalMinute'):l[key]+=d
  for key in ('departure','arrival'):
   m=l[key+'Minute']%1440;l[key]=f'{m//60:02}:{m%60:02}'
  for assignment in c['bankAssignments']:
   if assignment['legId']!=l['id']:continue
   operation=assignment['operation'];minute=l[operation+'Minute']%1440;city=l['destination']if operation=='arrival'else l['origin']
   old=next(b for b in c['hubBanks']if b['id']==assignment['bankId'])
   if old['startMinute']<=minute<old['endMinute']:continue
   bank=next((b for b in c['hubBanks']if b['hub']==city and b['startMinute']<=minute<b['endMinute']),None)
   if bank:reassigned.append({'flight':l['flight'],'operation':operation,'from':assignment['bankId'],'to':bank['id']});assignment['bankId']=bank['id']
 o=validate_operating_rules(c);structural=validate_schedule(c);overnight=validate_overnight_turns(c)
 try:
  g=export_gate_schedule(c);stands=[s for city in g['cities']for s in city['claims']if s['rowType']=='stand'];physical={'pass':True,'standClaims':len(stands),'standMinutes':sum(s['end']-s['start']for s in stands)}
 except Exception as e:physical={'pass':False,'error':str(e)}
 errors=[{'check':k['id'],'findings':k['findings']}for k in o['checks']if k['status']=='fail']
 info={'changes':[{'flight':l['flight'],'route':l['route'],'origin':l['origin'],'destination':l['destination'],'departure':l['departure'],'arrival':l['arrival'],'shift':changes[l['flight']]}for l in c['legs']if l['flight']in changes],'newBanks':new_banks,'bankReassignments':reassigned,'structural':structural['summary'],'operating':o['summary'],'overnight':{'status':overnight['status'],'findings':overnight['findings']},'physical':physical,'errors':errors}
 report['cases'][name]=info
 overlay={'schemaVersion':'1.0.0','id':'schedule-7-v1.3.0-proposed-'+name,'baseSchedule':{'scheduleId':base['schedule']['id'],'canonical':BASE.relative_to(ROOT).as_posix(),'sha256':report['baseSha256']},'schedule':{'id':'schedule_7_v1_3_0_proposal_'+name,'version':'1.3.0-analysis','label':'Unpublished v1.3.0 proposal '+name,'status':'draft'},'approval':{'status':'analysis only; not approved for implementation','publication':'Not authorized'},'retimeLegs':[{'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':l['departureMinute']+changes[l['flight']],'arrivalMinute':l['arrivalMinute']+changes[l['flight']]}for l in base['legs']if l['flight']in changes],'bankAssignmentReplacements':[{'legId':next(l['id']for l in base['legs']if l['flight']==x['flight']),'operation':x['operation'],'bankId':x['to']}for x in reassigned],'hubBanksToAdd':new_banks,'hubBankCountOverrides':{'PHF':c['operatingPolicy']['hubBankCounts']['PHF']}if new_banks else {}}
 replay=apply_optimization_overlay(base,overlay)
 assert replay['legs']==c['legs'] and replay['hubBanks']==c['hubBanks'] and replay['bankAssignments']==c['bankAssignments'] and replay['operatingPolicy']==c['operatingPolicy']
 proposals=ROOT/'config/proposals';proposals.mkdir(parents=True,exist_ok=True)
 (proposals/('schedule_7_v1_3_0_'+name+'.json')).write_text(json.dumps(overlay,indent=2)+'\n')
 c['schedule']=replay['schedule'];c['gatePlan']['label']=replay['gatePlan']['label']
 print(name,json.dumps(info),flush=True)
 (OUT/(name+'.json')).write_text(json.dumps(c,indent=2)+'\n')
 (OUT/(name+'_operating.json')).write_text(json.dumps(o,indent=2)+'\n')
 (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==report['baseSha256']
