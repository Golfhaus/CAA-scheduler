"""Accept round three and review five evening aircraft extensions; unpublished.

Reconstruct accepted changes from the released input. Timed screens retain
existing schedules, fully validate candidates and audit complete itineraries.
"""
from copy import deepcopy
import sys
from analyze_schedule_7_v1_2_3_round_3 import *
import analyze_schedule_7_v1_2_3_round_3 as previous
from analyze_schedule_7_v1_2_2_late_originators import route_finish

MASTER='config/optimizations/schedule_7_v1_2_3_accepted_rounds_1_3.json'
OUT='config/proposals/schedule_7_v1_2_3_round_4_screen.json'
original_overlay=previous.overlay

def overlay(s,plans,changes=(),banks=()):
    c=original_overlay(s,plans,changes,banks)
    mapping={l['id']:l['id'].replace('V123-R3-','V123-R4-') for l in c['insertLegs']}
    for l in c['insertLegs']:l['id']=mapping[l['id']]
    for a in c['bankAssignmentsToAdd']:a['legId']=mapping[a['legId']]
    c['id']='schedule-7-v1.2.3-round-4-screen'
    c['schedule'].update(id='schedule_7_v1_2_3_round_4_analysis',label='Schedule 7 v1.2.3 evening extension analysis; unpublished')
    return c

def accept():
    released=read_json(ROOT/RELEASE)
    c=deepcopy(read_json(ROOT/ACCEPTED))
    third=read_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_3.json')
    for key in ('insertLegs','retimeLegs','bankAssignmentsToAdd','bankAssignmentReplacements','hubBankChanges'):
        c.setdefault(key,[]).extend(deepcopy(third.get(key,[])))
    c['id']='schedule-7-v1.2.3-accepted-rounds-1-3'
    c['approval']['userInstruction'] += ' Add the 526 and 509 extensions.'
    c['approval']['scope'] += ' Morning DAL–MCI on 526; Flight 1206 +12 minutes; SAT–DAL on 509; 163 retained.'
    # Combined replay must preserve the sequentially reviewed flight IDs/numbers.
    intermediate=apply_optimization_overlay(released,read_json(ROOT/ACCEPTED))
    sequential=apply_optimization_overlay(intermediate,third)
    s=HoldSearch(released)
    v,t=validate(s,c)
    assert good(v),v
    assert sequential['legs']==t['legs'],'Flattening changed accepted flights'
    write_json(ROOT/MASTER,c);write_json(ROOT/BASE,t)
    print('ACCEPTED',len(t['legs']),'flights, 0 errors; unpublished',flush=True)
    return v,t

def inventory(s,r):
    legs=sorted((l for l in s.base['legs'] if l['route']==r),key=lambda l:l['sequenceWithinRoute'])
    last=legs[-1];days=sorted({l['day'] for l in s.base['legs'] if l['line']==last['line']})
    nextday=days[(days.index(last['day'])+1)%len(days)]
    following=min((l for l in s.base['legs'] if l['line']==last['line'] and l['day']==nextday),key=lambda l:l['sequenceWithinRoute'])
    finish=route_finish(s,legs)
    return {'route':r,'line':last['line'],'day':last['day'],'fleet':last['fleet'],
        'terminator':last['destination'],'finishMinute':finish,'arrival':last['arrival'],
        'nextOriginator':{k:following[k] for k in ('route','flight','origin','departure','departureMinute','line','day')},
        'legs':legs,'alreadyAddedEveningFlying':[l for l in legs if l['id'].startswith('V123') and l['departureMinute']>1100],
        'blockMinutes':sum(s.screen.utc(l)[2] for l in legs)}

def main():
    v,t=accept();s=HoldSearch(t)
    previous.overlay=overlay
    report={'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'acceptedValidation':v,
        'status':'analysis-only; new extensions not implemented; publication reserved to user',
        'model':'Pinned O-D, seat-uncapped relative-choice opportunity, not forecast loads or incremental passengers',
        'inventory':[inventory(s,r) for r in (340,350,114,169,327)],'screens':[]}
    old=read_json(ROOT/OUT) if (ROOT/OUT).exists() and '--fresh' not in sys.argv else {}
    assert not old or old['baseSha256']==report['baseSha256'],'Stale round-four checkpoint'
    def add(name,r,city,fleet,start,end,markets,changes=(),limit=5):
        x=next((z for z in old.get('screens',[]) if z['name']==name),None)
        x=x or previous.shortlist(s,name,r,city,fleet,start,end,markets,changes=changes,limit=limit)
        report['screens'].append(x);write_json(ROOT/OUT,report)
        return x
    for item in report['inventory']:
        r=item['route'];city=item['terminator'];fleet=item['fleet']
        # Departures must obey curfews; returns can occur after 23:30, even
        # after midnight, and must preserve the cyclic next originator.
        start=item['finishMinute']+40
        end=min(1560,item['nextOriginator']['departureMinute']+1440-40)
        markets=[d for d in s.screen.cities if d!=city and s.screen.utc(s.leg(city,d,0,fleet))[2]<=(end-start-40)/2]
        add(f'{r} evening, unchanged existing clocks',r,city,fleet,start,end,markets)
    for item in report['screens']:
        for x in item['selected'][:3]:
            if 'demand' in x:continue
            c=overlay(s,x['plans'],x['retimings']);_,trial=validate(s,c)
            x['demand']=demand(s,trial,{l['id'] for l in c['insertLegs']});x['reviewAudit']=audit(s,trial)
            print('AUDIT',item['name'],x['plans'][0]['city'],[(round(f['total'],1),f['departureClock'],f['arrivalClock']) for f in x['demand']['flights']],flush=True)
            write_json(ROOT/OUT,report)
    write_json(ROOT/OUT,report)

if __name__=='__main__':main()
