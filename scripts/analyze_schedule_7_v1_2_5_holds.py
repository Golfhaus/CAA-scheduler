"""Review four long holds against the accepted MCI draft; no automatic acceptance."""
from pathlib import Path
from copy import deepcopy
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay,demand,retime
from analyze_schedule_7_v1_2_3_round_3 import audit
import analyze_schedule_7_v1_2_3_round_3 as screen_module
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4 import cache_network,validate
from review_crj200_line_alignment import routes
BASE='data/schedules/schedule_7_v1_2_5_draft/canonical_schedule.json'
REPORT='config/proposals/schedule_7_v1_2_5_holds_review.json'
MAPPING={111:159,176:130,318:318,122:161}

def overlay(s,plans,changes=(),banks=()):
    c=make_overlay(s,plans,banks=banks,retimings=changes);c['id']='schedule-7-v1.2.5-long-holds-analysis'
    c['baseSchedule'].update(canonical=BASE,sha256=sha256_file(ROOT/BASE))
    c['schedule'].update(id='schedule_7_v1_2_5_holds_analysis',version='1.2.5-analysis',label='Unpublished v1.2.5 long-hold proposal')
    mapping={l['id']:l['id'].replace('V123-','V125-HOLDS-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    c['approval']={'status':'analysis only; not added to draft','publication':'Reserved to user decision'}
    return c

def inventory(base):
    rows=routes(base);result=[]
    for original,current in MAPPING.items():
        ls=rows[current]
        a,b=next((a,b) for a,b in zip(ls,ls[1:]) if a['destination']==b['origin'] and b['departureMinute']-a['arrivalMinute']>=330)
        result.append({'releasedRoute':original,'route':current,'line':a['line'],'day':a['day'],'fleet':a['fleet'],'station':a['destination'],'arrival':a['arrival'],'departure':b['departure'],'holdMinutes':b['departureMinute']-a['arrivalMinute'],'before':a,'after':b,'routeFlights':ls})
    return result

def review(s,name,plans,changes=(),bank_changes=()):
    c=overlay(s,plans,changes);c['hubBankChanges']=list(bank_changes);v,t=validate(s,c)
    x={'name':name,'plans':plans,'retimings':list(changes),'hubBankChanges':list(bank_changes),'validation':{k:v for k,v in v.items() if k!='affectedStations'}}
    if good(v):
        x['demand']=demand(s,t,{l['id'] for l in c['insertLegs']})
        for f in x['demand']['flights']:
            refs=f.pop('connectingFlights');f.update(connectingFlightCount=len(refs),connectingFlightNumbers=[l['flight'] for l in refs])
        x['connectionAudit']=audit(s,t)
        options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
        x['changedFlightConnections']=[]
        for timing in changes:
            identifier=timing['legId'];before={tuple(r['legs']) for r in s.screen.connections[identifier]};after={tuple(r['legs']) for r in records[identifier]}
            x['changedFlightConnections'].append({'flight':s.legs[identifier]['flight'],'lostConnectingChoices':len(before-after),'addedConnectingChoices':len(after-before)})
        write_json(ROOT/('config/proposals/schedule_7_v1_2_5_holds_'+name.lower()+'.json'),c)
    print('REVIEW',name,'valid',good(v),'scores',[(f['route'],f['origin'],f['destination'],f['departureClock'],f['arrivalClock'],round(f['total'],1)) for f in x.get('demand',{}).get('flights',[])],flush=True)
    return x,c,t

def main():
    args=argparse.ArgumentParser();args.add_argument('--screen',action='store_true');args.add_argument('--review',action='store_true');args.add_argument('--refine',action='store_true');args.add_argument('--joint',action='store_true');args.add_argument('--cases',default='');opts=args.parse_args()
    base=read_json(ROOT/BASE);s=HoldSearch(base);cache_network(s)
    r=read_json(ROOT/REPORT) if (ROOT/REPORT).exists() else {'status':'analysis only; MCI package accepted; new hold flying not added','baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'model':'Pinned O-D, seat-uncapped relative-choice one/two-stop opportunity; not passenger forecasts or incremental loads','inventory':inventory(base),'screens':[],'reviews':[]}
    assert r['baseSha256']==sha256_file(ROOT/BASE),'Stale hold checkpoint'
    screen_module.overlay=overlay;screen_module.validate=validate
    if opts.screen:
        for row in r['inventory']:
            name='R'+str(row['releasedRoute'])+'_UNCHANGED'
            if any(x['name']==name for x in r['screens']):continue
            city=row['station'];markets=sorted(s.screen.hubs) if city!='SYR' else [d for d in s.screen.cities if d!=city and len(s.pairs[city,d])<=3]
            x=screen_module.shortlist(s,name,row['route'],city,row['fleet'],row['before']['arrivalMinute']+40,row['after']['departureMinute']-40,markets,limit=8)
            r['screens'].append(x);write_json(ROOT/REPORT,r)
    if opts.refine:
        refine(s,r)
    if opts.joint:
        joint(s,r)
        florida_and_hpn_cases(s,r)
    if opts.review:
        chosen=set(opts.cases.split(',')) if opts.cases else None
        for screen in r['screens']:
            for item in screen['selected']:
                p=item['plans'][0];name=screen['name']+'_'+p['city']
                if chosen is not None and name not in chosen:continue
                if any(x['name']==name for x in r['reviews']):continue
                x,_,_=review(s,name,item['plans'],item['retimings'],screen.get('hubBankChanges',[]));r['reviews'].append(x);write_json(ROOT/REPORT,r)
    recommended='config/proposals/schedule_7_v1_2_5_holds_joint_hpn_early.json'
    if any(x['name']=='JOINT_HPN_EARLY' and good(x['validation']) for x in r['reviews']):
        r.update(recommendedCandidate='JOINT_HPN_EARLY',recommendedOverlay=recommended,recommendedOverlaySha256=sha256_file(ROOT/recommended),
                 decision={'strong':[159,130],'conditionalDirectionalFeeders':[318,161],
                           'reason':'PHF turns support both directions. BTV/HPN provide B3 feeders but weak positioning legs; HPN fills its missing morning SYR departure. Florida retimings remain optional alternatives.'})
    write_json(ROOT/REPORT,r)

def refine(s,r):
    """Resolve coarse-screen misses, preserve explicit bank and cascade checks."""
    changes=retime(s,161,[0,2,2,0,0,0])+retime(s,704,[0,0,0,0,2,2,0,0,0,0])
    bc=[{'bankId':'DAY-B5','expectedStartMinute':800,'expectedEndMinute':860,'startMinute':802,'endMinute':862}]
    name='R122_TWO_MINUTES'
    def shifted_overlay(search,plans,changes=(),banks=()):
        c=overlay(search,plans,changes,banks);c['hubBankChanges']=bc;return c
    if not any(x['name']==name for x in r['screens']):
        screen_module.overlay=shifted_overlay
        markets=[d for d in s.screen.cities if d!='SYR' and len(s.pairs['SYR',d])<=3]
        x=screen_module.shortlist(s,name,161,'SYR','CRJ200',378,630,markets,changes=changes,limit=8)
        x['hubBankChanges']=bc;r['screens'].append(x);write_json(ROOT/REPORT,r)
    cases=[]
    for out,back in [(510,627),(505,625),(495,620),(480,605),(470,605),(475,605)]:
        p={'route':130,'city':'PHF','legs':[s.leg('SWF','PHF',out,'CRJ200'),s.leg('PHF','SWF',back,'CRJ200')]}
        cases.append((f'R176_PHF_{out}_{back}',[p],[],[]))
    for city,out,back,shift in [('BTV',500,592,4),('BTV',505,597,9),('HPN',501,595,9),('ISP',490,588,6),('MHT',485,585,5)]:
        p={'route':318,'city':city,'legs':[s.leg('SYR',city,out,'CRJ700'),s.leg(city,'SYR',back,'CRJ700')]}
        cases.append((f'R318_{city}_DELAY{shift}',[p],retime(s,318,[0,shift,0,0]),[]))
    for city in ['ISP','HPN','BTV']:
        p=next(x['plans'][0] for sc in r['screens'] if sc['name']==name for x in sc['selected'] if x['plans'][0]['city']==city)
        cases.append((name+'_'+city,[p],changes,bc))
    for name,plans,changes,banks in cases:
        if any(x['name']==name for x in r['reviews']):continue
        x,_,_=review(s,name,plans,changes,banks);r['reviews'].append(x);write_json(ROOT/REPORT,r)

def joint(s,r):
    """Check all four additions together, including shared-bank/gate interactions."""
    common=[{'route':159,'city':'PHF','legs':[s.leg('ALB','PHF',615,'CRJ200'),s.leg('PHF','ALB',800,'CRJ200')]},
            {'route':130,'city':'PHF','legs':[s.leg('SWF','PHF',480,'CRJ200'),s.leg('PHF','SWF',605,'CRJ200')]}]
    changes=retime(s,161,[0,2,2,0,0,0])+retime(s,704,[0,0,0,0,2,2,0,0,0,0])
    bc=[{'bankId':'DAY-B5','expectedStartMinute':800,'expectedEndMinute':860,'startMinute':802,'endMinute':862}]
    for name,d318,out318,back318,delay,d161,back161 in [('JOINT_BUFFERED','BTV',505,597,9,'ISP',572),('JOINT_EARLY','BTV',465,588,0,'ISP',572),('JOINT_NEW_AVP','AVP',505,591,0,'BTV',578)]:
        if any(x['name']==name for x in r['reviews']):continue
        p318={'route':318,'city':d318,'legs':[s.leg('SYR',d318,out318,'CRJ700'),s.leg(d318,'SYR',back318,'CRJ700')]}
        p161={'route':161,'city':d161,'legs':[s.leg('SYR',d161,465,'CRJ200'),s.leg(d161,'SYR',back161,'CRJ200')]}
        x,_,_=review(s,name,common+[p318,p161],changes+retime(s,318,[0,delay,0,0]),bc)
        r['reviews'].append(x);write_json(ROOT/REPORT,r)

def florida_and_hpn_cases(s,r):
    common=[{'route':159,'city':'PHF','legs':[s.leg('ALB','PHF',615,'CRJ200'),s.leg('PHF','ALB',800,'CRJ200')]},
            {'route':130,'city':'PHF','legs':[s.leg('SWF','PHF',480,'CRJ200'),s.leg('PHF','SWF',605,'CRJ200')]}]
    bc=[{'bankId':'DAY-B5','expectedStartMinute':800,'expectedEndMinute':860,'startMinute':802,'endMinute':862}]
    for name,city,back,feed in [('JOINT_FLORIDA_FEED','ISP',572,True),('JOINT_HPN_FLORIDA_FEED','HPN',576,True),('JOINT_HPN_EARLY','HPN',576,False)]:
        if any(x['name']==name for x in r['reviews']):continue
        p318={'route':318,'city':'BTV','legs':[s.leg('SYR','BTV',500 if feed else 465,'CRJ700'),s.leg('BTV','SYR',592 if feed else 588,'CRJ700')]}
        p161={'route':161,'city':city,'legs':[s.leg('SYR',city,465,'CRJ200'),s.leg(city,'SYR',back,'CRJ200')]}
        changes=retime(s,161,[0,2,2,0,0,0])+retime(s,704,[0,0,0,0,2,2,0,0,0,0])
        if feed:
            changes+=retime(s,318,[0,4,0,0])
            for flight,shift in [(1300,-1),(1127,-4),(1228,-4),(1049,-5)]:
                leg=next(l for l in s.base['legs'] if l['flight']==flight)
                changes.append({'legId':leg['id'],'expectedDepartureMinute':leg['departureMinute'],'expectedArrivalMinute':leg['arrivalMinute'],'departureMinute':leg['departureMinute']+shift,'arrivalMinute':leg['arrivalMinute']+shift})
        x,_,_=review(s,name,common+[p318,p161],changes,bc);r['reviews'].append(x);write_json(ROOT/REPORT,r)

if __name__=='__main__':main()
