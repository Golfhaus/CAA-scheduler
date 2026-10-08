"""Start unpublished v1.2.4 and screen evening utilization on 126/518/308.

350 is user-approved. All other flying is analysis only. Immutable released
v1.2.3 is the replay base; checkpoint hashes prevent resuming stale analysis.
"""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay, validate as raw_validate, demand, retime
from analyze_schedule_7_v1_2_3_round_3 import audit
import analyze_schedule_7_v1_2_3_round_3 as screen_module
from analyze_schedule_7_v1_2_3_round_4 import inventory
from analyze_schedule_7_v1_2_3_utilization import good
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules

RELEASE='data/schedules/schedule_7_v1_2_3/canonical_schedule.json'
BASE='data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'
ACCEPTED='config/optimizations/schedule_7_v1_2_4_accepted_350.json'
OUT='config/proposals/schedule_7_v1_2_4_evening_screen.json'

def overlay(s,plans,changes=(),banks=()):
    c=make_overlay(s,plans,banks=banks,retimings=changes)
    path=RELEASE if s.base['schedule']['id']=='schedule_7_v1_2_3' else BASE
    c['baseSchedule'].update(canonical=path,sha256=sha256_file(ROOT/path))
    c['id']='schedule-7-v1.2.4-utilization-analysis'
    c['schedule'].update(id='schedule_7_v1_2_4_analysis',version='1.2.4',label='Schedule 7 v1.2.4 utilization analysis; unpublished')
    mapping={l['id']:l['id'].replace('V123-','V124-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    return c

def validate(s,c):
    # Existing authorization allows useful additional hub connectivity only.
    # No turn, gate, curfew, frequency, spacing or bank exception is added.
    t=apply_optimization_overlay(s.base,c)
    op=validate_operating_rules(t)
    for check in op['checks']:
        if check['id']!='tiered_service_minimums':continue
        for f in check['findings']:
            e=f['evidence']
            if f.get('override') or len(e.get('connectedHubs',[]))<=e.get('hubCountCap',999):continue
            if e.get('totalFlights',0)<e.get('minimumFlights',999) or e.get('hubOrFocusFlights',0)<e.get('minimumFlights',999):continue
            c['operatingOverrides'].append({'checkId':check['id'],'findingId':f['id'],
                'reason':'Standing user authorization permits useful additional hub service. Analysis remains unpublished; all physical and timing constraints remain enforced.'})
    return raw_validate(s,c)

def cache_network(s):
    enumerate_network=s.screen.enumerate;last={}
    def cached(legs):
        key=tuple((l['id'],l['origin'],l['destination'],l['departureMinute'],l['arrivalMinute']) for l in legs)
        if last.get('key')!=key:
            last.clear();last.update(key=key,options=enumerate_network(legs))
        return last['options']
    s.screen.enumerate=cached

def trial(s,name,plans,changes=(),banks=()):
    c=overlay(s,plans,changes,banks);v,t=validate(s,c)
    x={'name':name,'plans':plans,'retimings':list(changes),'banks':list(banks),'validation':v}
    if good(v):
        x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,t)
        loads,records=s.screen.allocate(s.screen.enumerate(t['legs']))
        x['changedFlightConnections']=[]
        for change in changes:
            l=s.legs[change['legId']]
            before={tuple(r['legs']) for r in s.screen.connections[l['id']]}
            after={tuple(r['legs']) for r in records[l['id']]}
            x['changedFlightConnections'].append({'flight':l['flight'],
                'oldTotalOpportunity':sum(s.screen.loads[l['id']].values()),
                'newTotalOpportunity':sum(loads[l['id']].values()),
                'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before)})
    print('TRIAL',name,'errors',v['operatingErrors'],'gates',v['gates'],
          [(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x.get('demand',{}).get('flights',[])],flush=True)
    return x,c,t

def loop(s,r,a,b,out,back,fleet):
    return {'route':r,'city':b,'legs':[s.leg(a,b,out,fleet),s.leg(b,a,back,fleet)]}

def accept():
    s=HoldSearch(read_json(ROOT/RELEASE));cache_network(s)
    x,c,t=trial(s,'350 approved buffered evening MCI turn',[loop(s,350,'ELP','MCI',1107,1353,'CRJ700')])
    assert good(x['validation']),x['validation']
    c['id']='schedule-7-v1.2.4-accepted-350'
    c['schedule'].update(id='schedule_7_v1_2_4_draft',label='Schedule 7 v1.2.4 working draft; unpublished')
    c['approval']={'status':'approved for draft implementation; unpublished',
        'userInstruction':"Begin work on 1.2.4. Implement the addition to route 350; ELP's closest other MCI flight is midday.",
        'scope':'Route 350 ELP–MCI evening round trip; existing clocks retained.',
        'publication':'Reserved to user decision'}
    t=apply_optimization_overlay(s.base,c)
    write_json(ROOT/ACCEPTED,c);write_json(ROOT/BASE,t)
    write_json(ROOT/'config/proposals/schedule_7_v1_2_4_accepted_350_review.json',x)
    print('ACCEPTED 350',len(t['legs']),'flights; unpublished',flush=True)

def main():
    if '--accept' in sys.argv:accept();return
    s=HoldSearch(read_json(ROOT/BASE));cache_network(s)
    r=read_json(ROOT/OUT) if (ROOT/OUT).exists() else {
        'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),
        'status':'126/518/308 proposals only; 350 implemented in unpublished draft',
        'model':'Pinned O-D; seat-uncapped full-capture relative-choice one/two-stop opportunities, not forecast loads or incremental passengers',
        'inventory':[inventory(s,n) for n in (126,518,308)],'screens':[],'trials':[]}
    assert r['baseSha256']==sha256_file(ROOT/BASE),'Stale checkpoint'
    screen_module.overlay=overlay;screen_module.validate=validate
    def screen(name,*args,**kw):
        if any(x['name']==name for x in r['screens']):return
        x=screen_module.shortlist(s,name,*args,**kw);r['screens'].append(x);write_json(ROOT/OUT,r)
    def add(name,p,changes=(),banks=()):
        if any(x['name']==name for x in r['trials']):return
        x,c,t=trial(s,name,p,changes,banks);r['trials'].append(x);write_json(ROOT/OUT,r)
    if '--screens' in sys.argv:
        for item in r['inventory']:
            city=item['terminator'];fleet=item['fleet'];start=item['finishMinute']+40
            end=min(1560,item['nextOriginator']['departureMinute']+1440-40)
            markets=[d for d in s.screen.cities if d!=city and s.screen.utc(s.leg(city,d,0,fleet))[2]<=(end-start-40)/2]
            screen(f"{item['route']} unchanged evening",item['route'],city,fleet,start,end,markets,limit=4)
        return
    if '--rebuild' in sys.argv:
        changes=retime(s,518,[0,-90,-50,-34])
        screen('518 consolidate PIE hold; earlier SYR arrival',518,'SYR','CRJ900',1165,1500,
               [d for d in s.screen.cities if d!='SYR' and s.screen.utc(s.leg('SYR',d,0,'CRJ900'))[2]<=100],changes=changes,limit=4)
        changes=retime(s,308,[0,0,0,-7,-66,-75])
        screen('308 earlier final PHF turn',308,'CLT','CRJ700',1146,1560,
               sorted(s.screen.hubs),changes=changes,limit=3)
        return
    if '--holistic' in sys.argv:
        # An earlier B6 arrival collides with Flight 1231's 16:05 PIE
        # departure. Rebuild into B5 instead, keeping other aircraft intact.
        changes=retime(s,518,[-50,-145,-140,-140])
        screen('518 earlier PHF/PIE cycle; SYR-B5 arrival',518,'SYR','CRJ900',1059,1500,
               [d for d in s.screen.cities if d!='SYR' and s.screen.utc(s.leg('SYR',d,0,'CRJ900'))[2]<=120],
               changes=changes,limit=5)
        return
    if '--holistic2' in sys.argv:
        # Keep 30 minutes clear of Route 519's 08:55 PIE–PHF departure.
        # The first PHF flight moves into M0, with all other aircraft intact.
        changes=retime(s,518,[-90,-170,-145,-140])
        screen('518 rebuild into PHF-M0/M1 and SYR-B5',518,'SYR','CRJ900',1059,1500,
               [d for d in s.screen.cities if d!='SYR' and s.screen.utc(s.leg('SYR',d,0,'CRJ900'))[2]<=120],
               changes=changes,limit=5)
        return
    if '--trials' in sys.argv:
        add('126 buffered MLB–JAX',[loop(s,126,'MLB','JAX',1200,1302,'CRJ200')])
        # Explicit late BHM timings: earlier high-scoring choices can fail its
        # fixed gate inventory. Do not mistake that for an all-evening failure.
        for route,city,fleet,out in [(126,'MLB','CRJ200',1245),(126,'MLB','CRJ200',1260),
                                    (308,'CLT','CRJ700',1245),(308,'CLT','CRJ700',1260)]:
            a=s.leg(city,'BHM',out,fleet)['arrivalMinute']
            add(f'{route} late BHM {out}',[loop(s,route,city,'BHM',out,a+50,fleet)])
        changes=retime(s,518,[0,-90,-50,-34])
        add('518 rebuilt SYR–BUF',[loop(s,518,'SYR','BUF',1173,1260,'CRJ900')],changes)
        add('518 rebuilt SYR–ROC',[loop(s,518,'SYR','ROC',1175,1255,'CRJ900')],changes)
        changes=retime(s,308,[0,0,0,-7,-66,-75])
        add('308 rebuilt CLT–DAY',[loop(s,308,'CLT','DAY',1146,1285,'CRJ700')],changes)
        return
    if '--audit' in sys.argv:
        for item in r['screens']:
            for selected in item['selected'][:(5 if 'PHF-M0/M1' in item['name'] else 2)]:
                add(item['name']+' '+selected['plans'][0]['city'],selected['plans'],selected['retimings'])
        return
    if '--joint' in sys.argv:
        plans=[loop(s,126,'MLB','JAX',1200,1302,'CRJ200'),
               loop(s,308,'CLT','MCI',1230,1365,'CRJ700')]
        x,c,t=trial(s,'126 JAX and 308 MCI jointly; 518 retained',plans)
        assert good(x['validation']),x['validation']
        c['id']='schedule-7-v1.2.4-proposed-126-308'
        c['approval']={'status':'proposed; not implemented',
                      'scope':'126 buffered MLB–JAX; 308 late CLT–MCI; retain 518.',
                      'publication':'Reserved to user decision'}
        write_json(ROOT/'config/proposals/schedule_7_v1_2_4_proposed_126_308.json',c)
        r['recommendedJointProposal']=x;write_json(ROOT/OUT,r)
        return
    raise SystemExit('Choose --accept, --screens, --rebuild, --trials, --holistic, --holistic2, --audit or --joint')

if __name__=='__main__':main()
