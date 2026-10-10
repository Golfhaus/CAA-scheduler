"""Small, explicit timing adjustments for midnight hub exchanges; review only."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import analyze_schedule_7_v1_2_4_hub_swaps as e
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import validate,demand,retime
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_4 import cache_network
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules
from analyze_schedule_7_v1_2_4_xna import maintenance
from analyze_schedule_7_v1_2_3_round_4 import inventory

def operating_evidence(base, trial, lines):
    before={x['id']:x for x in validate_operating_rules(base)['checks']}
    after={x['id']:x for x in validate_operating_rules(trial)['checks']}
    b={x['id']:x['evidence'] for x in before['section_26_city_departure_gap']['findings']}
    a={x['id']:x['evidence'] for x in after['section_26_city_departure_gap']['findings']}
    worse=[city for city,x in a.items() if city in b and
           max(g['minutes'] for g in x['excessiveGaps'])>
           max(g['minutes'] for g in b[city]['excessiveGaps'])]
    return {'section26':{'checkA':after['section_26_pairing_spacing']['status'],
                        'newCheckBFindings':len(set(a)-set(b)),
                        'worsenedCheckBGaps':len(worse),'worsenedCities':worse},
            'maintenance':{line:maintenance(trial,line) for line in sorted(lines)}}

def main():
    s,r,routes=e.load()
    report={'baseCanonical':e.BASE,'baseSha256':sha256_file(ROOT/e.BASE),'status':'Analysis only; original accepted draft unchanged.','candidates':[]}
    tests=[('MID-RETIME-337-345',337,345,[(1404,-12),(1319,-16),(1320,-16)],(1245,1224)),
           ('MID-RETIME-712-722',712,722,[(2001,-2)],(1235,1292)),
           ('MID-RETIME-337-345-PRESERVE',337,345,[(1404,-12),(1319,-16),(1320,-16),(1784,-3),(1589,-1)],(1245,1224))]
    for name,a,b,clock_changes,deps in tests:
        c0={'baseSchedule':{'scheduleId':s.base['schedule']['id']},'schedule':deepcopy(s.base['schedule']),
            'retimeLegs':[],'hubBankChanges':[]}
        for number,delta in clock_changes:
            old=next(l for l in s.base['legs'] if l['flight']==number)
            c0['retimeLegs'].append({'legId':old['id'],'expectedDepartureMinute':old['departureMinute'],'expectedArrivalMinute':old['arrivalMinute'],
                'departureMinute':old['departureMinute']+delta,'arrivalMinute':old['arrivalMinute']+delta})
        if a==337:
            # Move the whole 60-minute MCI bank one minute earlier, rather than
            # permit the ELP inbound flight to arrive outside its bank.
            for start in (885,1185):
                bank=next(x for x in s.base['hubBanks'] if x['hub']=='MCI' and x['startMinute']==start)
                c0['hubBankChanges'].append({'bankId':bank['id'],'expectedStartMinute':start,'expectedEndMinute':start+60,
                                            'startMinute':start-1,'endMinute':start+59})
        timed=HoldSearch(apply_optimization_overlay(s.base,c0));cache_network(timed)
        trs={route:inventory(timed,route) for route in routes}
        for route,x in trs.items():x['originator']=x['legs'][0]['origin'];x['startMinute']=x['legs'][0]['departureMinute']
        legs=[timed.leg(trs[x]['terminator'],trs[y]['terminator'],dep,trs[x]['fleet']) for x,y,dep in ((a,b,deps[0]),(b,a,deps[1]))]
        assert all(l['arrivalMinute']<=1441 for l in legs)
        q={'id':name,'routes':[a,b],'fleet':trs[a]['fleet'],'lines':[trs[a]['line'],trs[b]['line']],
            'selectedTiming':{'legs':legs,'rons':[1440+trs[y]['nextOriginator']['departureMinute']-leg['arrivalMinute'] for y,leg in zip((b,a),legs)]}}
        pool0=set(q['lines']);others=sorted({x['line'] for x in trs.values() if x['fleet']==q['fleet']}-pool0)
        attempts=[];proof=None
        # Broaden the earlier three-line limit to four line pools if needed.
        for n in range(min(3,len(others))+1):
            for extra in combinations(others,n):
                pool=pool0|set(extra);count=sum(x['line'] in pool for x in trs.values())
                if not any(9*k<=count<=12*k for k in range(1,count//9+1)):continue
                found=e.line_cover(timed,q,trs,pool,seconds=2)
                attempts.append({k:found[k] for k in ('poolLines','routeCount','status','elapsedSeconds')})
                if found['status']=='proved':proof=found;break
            if proof:break
        if not proof:
            report['candidates'].append({'id':name,'status':'No compliant line cover proved','retimings':c0['retimeLegs'],'attempts':attempts})
            print('RETIME',name,'NO LINE COVER',flush=True);continue
        q['lineProof']=proof
        c=e.candidate_overlay(timed,q,trs)
        c['baseSchedule']['sha256']=sha256_file(ROOT/e.BASE)
        c['retimeLegs']=c0['retimeLegs'];c['hubBankChanges']=c0['hubBankChanges']
        c['approval']['scope']='Explicit small retimings, reciprocal extension legs, bank changes and full line reconstruction. No change implemented.'
        v,t=validate(s,c)
        item={'id':name,'routes':[a,b],'retimings':c0['retimeLegs'],'bankChanges':c0['hubBankChanges'],'lineProof':proof,'validation':v,
              'addedLegs':legs,'proposedBanks':c['hubBanksToAdd']}
        item.update(operating_evidence(s.base,t,proof['poolLines']))
        if e.good(v):
            item['demand']=demand(s,t,{l['id'] for l in c['insertLegs']});item['connectionAudit']=audit(s,t)
            path='config/proposals/schedule_7_v1_2_4_'+name.lower().replace('-','_')+'.json'
            write_json(ROOT/path,c);item['overlay']=path
        report['candidates'].append(item)
        write_json(ROOT/'config/proposals/schedule_7_v1_2_4_midnight_retimings_review.json',report)
        print('RETIME',name,v['operatingErrors'],v['gates'],proof['cycleLengths'],[(f['origin']+'-'+f['destination'],round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in item.get('demand',{}).get('flights',[])],
              item.get('connectionAudit',{}),flush=True)
    write_json(ROOT/'config/proposals/schedule_7_v1_2_4_midnight_retimings_review.json',report)

if __name__=='__main__':main()
