"""Unpublished v1.2.3 BWI aircraft utilization and DAY bank feasibility."""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_2_late_originators import route_finish
from analyze_schedule_7_v1_2_2_sfb_evenings import clock
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.gates import GateCapacityError

BASE = 'data/schedules/schedule_7_v1_2_2/canonical_schedule.json'
REPORT = 'config/proposals/schedule_7_v1_2_3_bwi_screen.json'
DAY_BANK = {'id': 'DAY-B9', 'hub': 'DAY', 'startMinute': 1265, 'endMinute': 1325}


def make_overlay(search, plans, banks=(), retimings=()):
    additions, assignments, replacements = [], [], []
    available = search.base['hubBanks'] + list(banks)
    def bank(city, minute):
        return next((b['id'] for b in available if b['hub']==city and
                     b['startMinute'] <= minute % 1440 < b['endMinute']), None)
    for plan in plans:
        for leg in plan['legs']:
            index = 1 + sum(l['route']==plan['route'] for l in additions)
            item = {**leg, 'route': plan['route'],
                    'id': f"V123-R{plan['route']}-{index}-{leg['origin']}-{leg['destination']}"}
            additions.append(item)
            for op, city, minute in [('departure',leg['origin'],leg['departureMinute']),
                                    ('arrival',leg['destination'],leg['arrivalMinute'])]:
                if city in search.base['operatingPolicy']['hubs']:
                    assignment = bank(city, minute)
                    if assignment:
                        assignments.append({'legId':item['id'],'operation':op,'bankId':assignment})
    for retiming in retimings:
        old = search.legs[retiming['legId']]
        for assignment in search.base['bankAssignments']:
            if assignment['legId'] != old['id']:
                continue
            op = assignment['operation']
            city = old['origin'] if op=='departure' else old['destination']
            target = bank(city, retiming[op+'Minute'])
            if target and target != assignment['bankId']:
                replacements.append({'legId':old['id'],'operation':op,'bankId':target})
    return {'schemaVersion':'1.0.0','id':'schedule-7-v1.2.3-bwi-feasibility',
            'baseSchedule':{'scheduleId':search.base['schedule']['id'], 'canonical':BASE,
                            'sha256':sha256_file(ROOT / BASE)},
            'schedule':{'id':'schedule_7_v1_2_3_bwi_feasibility','version':'1.2.3-analysis',
                        'label':'Schedule 7 v1.2.3 BWI feasibility; unpublished','status':'draft'},
            'approval':{'status':'analysis-only','publication':'Reserved to user decision'},
            'hubBanksToAdd':list(banks),
            'hubBankCountOverrides':{hub:search.base['operatingPolicy']['hubBankCounts'][hub]+sum(b['hub']==hub for b in banks)
                                     for hub in {b['hub'] for b in banks}},
            'insertLegs':additions,'retimeLegs':list(retimings),
            'bankAssignmentsToAdd':assignments,'bankAssignmentReplacements':replacements,
            'operatingOverrides':[]}


def validate(search, change):
    trial = apply_optimization_overlay(search.base, change)
    op = validate_operating_rules(trial)
    overnight = validate_overnight_turns(trial)
    result = {'structural':validate_schedule(trial)['status'],
              'operatingErrors':op['summary']['effectiveErrorFindings'],
              'operatingWarnings':op['summary']['effectiveWarningFindings'],
              'hardStopFailures':[c['id'] for c in op['checks'] if c['hardStop'] and c['status']=='fail'],
              'blocking':[{'check':c['id'],'findings':[f for f in c['findings'] if not f.get('override')]}
                          for c in op['checks'] if c['severity']=='error' and c['status']=='fail'
                          and any(not f.get('override') for f in c['findings'])],
              'overnight':overnight['status'],'overnightFindings':overnight['findings'],
              'planning':validate_planning_snapshot(reconstruct_planning_snapshot(trial),trial)['status']}
    try:
        gates=export_gate_schedule(trial)
        stands=[c for city in gates['cities'] for c in city['claims'] if c['rowType']=='stand']
        result.update(gates='pass',standClaims=len(stands),standMinutes=sum(c['end']-c['start'] for c in stands),
                      affectedStations=[{**{k:v for k,v in city.items() if k!='claims'},
                          'standClaims':sum(c['rowType']=='stand' for c in city['claims']),
                          'standMinutes':sum(c['end']-c['start'] for c in city['claims'] if c['rowType']=='stand')}
                          for city in gates['cities'] if city['code'] in {'BWI','DAY','PHF','SYR','JAX','BHM'}])
    except GateCapacityError as error:
        result.update(gates='fail',gateFailure=str(error))
    return result,trial


def demand(search, trial, ids):
    options=search.screen.enumerate(trial['legs'])
    loads,records=search.screen.allocate(options)
    legs={l['id']:l for l in trial['legs']}
    result=[]
    for leg in trial['legs']:
        if leg['id'] not in ids: continue
        markets,groups=Counter(),Counter()
        connections=set()
        hub=leg['destination'] if leg['destination'] in search.screen.hubs else leg['origin']
        for r in records[leg['id']]:
            markets[r['origin'],r['destination']]+=r['opportunity']
            endpoint = r['destination'] if leg['destination']==hub else r['origin']
            groups[search.screen.cities[endpoint]['group']]+=r['opportunity']
            index=r['legs'].index(leg['id'])
            if leg['destination']==hub and index+1<len(r['legs']): connections.add(r['legs'][index+1])
            elif leg['origin']==hub and index: connections.add(r['legs'][index-1])
        result.append({**leg,'departureClock':clock(leg['departureMinute']),'arrivalClock':clock(leg['arrivalMinute']),
                       'blockMinutes':search.screen.utc(leg)[2],
                       'currentPairFrequency':len(search.pairs[leg['origin'],leg['destination']]),
                       'routeLocalOd':search.screen.od[leg['origin']][leg['destination']],
                       'local':loads[leg['id']]['local'],
                       'connecting':sum(v for k,v in loads[leg['id']].items() if k!='local'),
                       'total':sum(loads[leg['id']].values()),
                       'oneStop':sum(r['opportunity'] for r in records[leg['id']] if r['stops']==1),
                       'twoStop':sum(r['opportunity'] for r in records[leg['id']] if r['stops']==2),
                       'groups':dict(groups),
                       'connectingFlights':[ {k:legs[i][k] for k in ('flight','origin','destination','departure','arrival')} for i in sorted(connections)],
                       'topMarkets':[{'origin':a,'destination':b,'opportunity':v} for (a,b),v in markets.most_common(10)]})
    # Distinguish true newly connected markets from demand redistributed to added flights.
    new_market=sum(search.screen.od[a][b] for (a,b),choices in options.items() if choices and not search.screen.options.get((a,b)))
    improved=sum(bool(search.screen.options.get(od)) and min(c['elapsed'] for c in choices)<min(c['elapsed'] for c in search.screen.options[od])
                 for od,choices in options.items() if choices)
    return {'flights':result,'newlyConnectedMarketDemand':new_market,'marketsWithFasterBestItinerary':improved}


def quick_gates(search, route, added, kind, hub):
    """Conservative passenger touches; full cyclic allocation follows selection."""
    counts={c:search.occupancy[c][:] for c in {'BWI',hub}}
    label='330 -> 331' if kind=='morning' and route==331 else '331 -> 332'
    for city in search.gates['cities']:
        if city['code']=='BWI':
            for claim in city['claims']:
                if claim['label']==label and claim['rowType']=='gate':
                    search.mark(counts['BWI'],claim['start'],claim['end'],-1)
    def touch(city,start,end):
        if end-start<=150:search.mark(counts[city],start,end,1)
        else:
            search.mark(counts[city],start,start+45,1)
            search.mark(counts[city],end-60,end,1)
    first,second=added
    if kind=='morning':
        arrival=1278 if route==331 else 1152
        original=605 if route==331 else 465
        touch('BWI',arrival,1440+first['departureMinute'])
        touch('BWI',second['arrivalMinute'],original)
    else:
        touch('BWI',1152,first['departureMinute'])
        touch('BWI',second['arrivalMinute'],1440+465)
    touch(hub,first['arrivalMinute'],second['departureMinute'])
    return all(max(values)<=search.gate_capacity[city] for city,values in counts.items())


def morning(search, route):
    fleet='CRJ700';deadline=(605 if route==331 else 465)-40
    results=[]
    for hub in ('DAY','PHF','SYR','JAX','MCI','BHM'):
        duration=search.screen.utc(search.leg('BWI',hub,0,fleet))[2]
        choices=[]
        for dep in search.grid(270,deadline-2*duration-40):
            out=search.leg('BWI',hub,dep,fleet)
            if search.bank(hub,out['arrivalMinute']) is None: continue
            for back in search.grid(out['arrivalMinute']+40,deadline-search.leg(hub,'BWI',0,fleet)['arrivalMinute']):
                incoming=search.leg(hub,'BWI',back,fleet)
                if back-out['arrivalMinute']>180 or search.bank(hub,back) is None:continue
                if not search.spacing([out,incoming]) or not quick_gates(search,route,[out,incoming],'morning',hub):continue
                score,values=search.score([out,incoming])
                choices.append({'hub':hub,'route':route,'legs':[out,incoming],'score':score,'legScores':values,
                                'originatorBufferMinutes':deadline+40-incoming['arrivalMinute']})
        choices.sort(key=lambda c:-c['score'])
        item={'hub':hub,'route':route,'localOdEachWay':[search.screen.od['BWI'][hub],search.screen.od[hub]['BWI']],
              'existingFrequencyEachWay':[len(search.pairs['BWI',hub]),len(search.pairs[hub,'BWI'])],
              'timingChoices':len(choices),'screenedTop':choices[:5]}
        for choice in choices[:8]:
            change=make_overlay(search,[choice]);validation,trial=validate(search,change)
            if validation['operatingErrors'] or validation['gates']!='pass':
                item.setdefault('rejected',[]).append({'legs':choice['legs'],'validation':validation})
                continue
            ids={l['id'] for l in change['insertLegs']}
            item['selected']={**choice,'validation':validation,'demand':demand(search,trial,ids)}
            break
        results.append(item)
        print('morning',route,hub,len(choices),'selected',bool(item.get('selected')),flush=True)
    return results


def evening_day(search, overnight):
    fleet='CRJ700';choices=[]
    for dep in search.grid(1152+40,1260):
        out=search.leg('BWI','DAY',dep,fleet)
        if not DAY_BANK['startMinute']<=out['arrivalMinute']<DAY_BANK['endMinute']:continue
        returns=search.grid(300,465-50-82) if overnight else search.grid(out['arrivalMinute']+40,DAY_BANK['endMinute']-1)
        for back in returns:
            incoming=search.leg('DAY','BWI',back,fleet)
            if overnight:
                if search.bank('DAY',back) is None:continue
                gate_in={**incoming,'departureMinute':incoming['departureMinute']+1440,'arrivalMinute':incoming['arrivalMinute']+1440}
            else:gate_in=incoming
            if not search.spacing([out,incoming]) or not quick_gates(search,331,[out,gate_in],'evening','DAY'):continue
            score,values=search.score([out,incoming])
            plans=[{'route':331,'legs':[out]} , {'route':332,'legs':[incoming]}] if overnight else [{'route':331,'legs':[out,incoming]}]
            choices.append({'plans':plans,'score':score,'legScores':values,
                            'kind':'DAY-overnight' if overnight else 'DAY-same-night-return'})
    choices.sort(key=lambda c:-c['score'])
    result={'timingChoices':len(choices),'screenedTop':choices[:5]}
    for choice in choices[:12]:
        change=make_overlay(search,choice['plans'],[DAY_BANK]);validation,trial=validate(search,change)
        if validation['operatingErrors'] or validation['gates']!='pass':
            result.setdefault('rejected',[]).append({'plans':choice['plans'],'validation':validation});continue
        result['selected']={**choice,'validation':validation,'demand':demand(search,trial,{l['id'] for l in change['insertLegs']})}
        break
    print('evening',overnight,len(choices),'selected',bool(result.get('selected')),flush=True)
    return result


def named_trial(search, name, plans, banks=(), retimings=()):
    change=make_overlay(search,plans,banks,retimings)
    validation,trial=validate(search,change)
    result={'name':name,'plans':plans,'banks':list(banks),'retimings':list(retimings),'validation':validation}
    if not validation['operatingErrors'] and validation['gates']=='pass' and validation['overnight']=='pass':
        result['demand']=demand(search,trial,{l['id'] for l in change['insertLegs']})
        baseline_ids=set(search.legs)
        self_check={l['id']:l for l in trial['legs'] if l['id'] in baseline_ids}
        authorized={r['legId'] for r in retimings}
        for old in search.base['legs']:
            keys=('flight','route','line','day','fleet','origin','destination')
            if old['id'] not in authorized:keys+=('departureMinute','arrivalMinute')
            assert all(old[k]==self_check[old['id']][k] for k in keys)
    print('trial',name,validation['operatingErrors'],validation['gates'],flush=True)
    return result


def retime(search, route, changes):
    seq=sorted((l for l in search.base['legs'] if l['route']==route),key=lambda l:l['sequenceWithinRoute'])
    return [{'legId':l['id'],'expectedDepartureMinute':l['departureMinute'],
             'expectedArrivalMinute':l['arrivalMinute'],'departureMinute':l['departureMinute']+shift,
             'arrivalMinute':l['arrivalMinute']+shift}
            for l,shift in zip(seq,changes) if shift]


def alternatives(search):
    trials=[]
    legs=lambda city,out,back:[search.leg('BWI',city,out,'CRJ700'),search.leg(city,'BWI',back,'CRJ700')]
    trials.append(named_trial(search,'Buffered DAY morning on 331',[{'route':331,'legs':legs('DAY',343,473)}]))
    # A five-minute originator shift and three-minute return shift allow the
    # morning SYR bank without changing the rest of Route 331.
    trials.append(named_trial(search,'SYR morning on 331; two minor retimings',
        [{'route':331,'legs':legs('SYR',400,505)}],retimings=retime(search,331,[5,3,0,0,0])))
    # Test the wider 332 cascade rather than assuming its late first flight
    # leaves room for an additive, clock-preserving early turn.
    trials.append(named_trial(search,'PHF morning on 332; four-leg cascade',
        [{'route':332,'legs':legs('PHF',335,423)}],retimings=retime(search,332,[46,44,5,2,0,0,0])))
    for hub in ('PHF','BHM'):
        choices=[]
        for out in search.grid(1192,1260):
            first=search.leg('BWI',hub,out,'CRJ700')
            if search.bank(hub,first['arrivalMinute']) is None:continue
            for back in search.grid(first['arrivalMinute']+40,1410):
                last=search.leg(hub,'BWI',back,'CRJ700')
                if back-first['arrivalMinute']>180 or search.bank(hub,back) is None:continue
                if not search.spacing([first,last]) or not quick_gates(search,331,[first,last],'evening',hub):continue
                score,values=search.score([first,last]);choices.append((score,first,last))
        choices.sort(reverse=True,key=lambda row:row[0])
        for score,first,last in choices[:8]:
            t=named_trial(search,f'{hub} same-night evening alternative',[{'route':331,'legs':[first,last]}])
            if t.get('demand'):
                trials.append(t);break
    return trials


def day_feeders(search):
    """Existing early terminators that can add a legal late DAY round trip."""
    routes=defaultdict(list); results=[]
    for l in search.base['legs']:routes[l['route']].append(l)
    for seq in routes.values():seq.sort(key=lambda l:l['sequenceWithinRoute'])
    for route,seq in sorted(routes.items()):
        city,fleet=seq[-1]['destination'],seq[0]['fleet']
        if city=='DAY' or route==331:continue
        finish=route_finish(search,seq)
        if finish>1200:continue
        first_offset=search.leg(city,'DAY',0,fleet)['arrivalMinute']
        choices=[]
        for arrival in search.grid(DAY_BANK['startMinute'],DAY_BANK['endMinute']-51):
            dep=arrival-first_offset
            if dep<finish+40 or dep>(1410 if city in search.screen.hubs else 1260):continue
            out=search.leg(city,'DAY',dep,fleet)
            if search.bank(city,dep) is None:continue
            for back in search.grid(arrival+50,DAY_BANK['endMinute']-1):
                incoming=search.leg('DAY',city,back,fleet)
                if search.bank(city,incoming['arrivalMinute']) is None:continue
                if not search.spacing([out,incoming]):continue
                score,values=search.score([out,incoming])
                choices.append({'route':route,'city':city,'fleet':fleet,'plans':[{'route':route,'legs':[out,incoming]}],
                                'score':score,'legScores':values,'finish':clock(finish),
                                'currentFrequency':len(search.pairs[city,'DAY'])})
        choices.sort(key=lambda c:-c['score'])
        if not choices:continue
        item={'route':route,'city':city,'fleet':fleet,'finish':clock(finish),'timingChoices':len(choices),
              'currentFrequency':len(search.pairs[city,'DAY']),'localOdBothDirections':search.screen.od[city]['DAY']+search.screen.od['DAY'][city]}
        for choice in choices[:5]:
            t=named_trial(search,f'Late DAY feeder {route} {city}',choice['plans'],[DAY_BANK])
            if t.get('demand'):
                item['selected']={**choice,**t};break
            item.setdefault('rejected',[]).append(t)
        results.append(item)
    return sorted(results,key=lambda r:-r.get('selected',{}).get('score',0))


def joint_trials(search):
    leg=lambda a,b,t:search.leg(a,b,t,'CRJ700')
    phf={'route':331,'legs':[leg('BWI','PHF',335),leg('PHF','BWI',423)]}
    day={'route':331,'legs':[leg('BWI','DAY',1192),leg('DAY','BWI',1324)]}
    clt={'route':340,'legs':[leg('CLT','DAY',1188),leg('DAY','CLT',1315)]}
    sdf={'route':327,'legs':[leg('SDF','DAY',1217),leg('DAY','SDF',1315)]}
    mci_in=max((l for l in search.base['legs'] if l['route']==506),key=lambda l:l['sequenceWithinRoute'])
    night_retime=[{'legId':mci_in['id'],'expectedDepartureMinute':mci_in['departureMinute'],
        'expectedArrivalMinute':mci_in['arrivalMinute'],'departureMinute':mci_in['departureMinute']+20,
        'arrivalMinute':mci_in['arrivalMinute']+20}]
    strict=deepcopy(day);strict['legs'][1]=leg('DAY','BWI',1314)
    result=[
        named_trial(search,'Buffered DAY evening with unchanged existing flights',[phf,day],[DAY_BANK]),
        named_trial(search,'Strict minimum-turn DAY bank with CLT/SDF feeders',[phf,strict,clt,sdf],[DAY_BANK]),
        named_trial(search,'Simpler eight-flight plan',[phf,day,clt,sdf],[DAY_BANK],night_retime),
        named_trial(search,'DAY morning instead of PHF on 331',
            [{'route':331,'legs':[leg('BWI','DAY',343),leg('DAY','BWI',473)]},day,clt,sdf],[DAY_BANK],night_retime),
        named_trial(search,'Longer PHF morning hold with buffered return',
            [{'route':331,'legs':[leg('BWI','PHF',335),leg('PHF','BWI',505)]}]),
        named_trial(search,'DAY turns and late-bank feeders; preserve every existing flight',
            [{'route':331,'legs':[leg('BWI','DAY',343),leg('DAY','BWI',473),*strict['legs']]},clt,sdf],[DAY_BANK]),
    ]
    wider=[{'route':331,'legs':[leg('BWI','DAY',359),leg('DAY','BWI',481),*day['legs']]},
           {'route':332,'legs':[leg('BWI','PHF',335),leg('PHF','BWI',423)]},clt,sdf]
    retimings=night_retime+retime(search,332,[46,44,5,2,0,0,0])+retime(search,507,[-6,0,0,0,0,0])
    result.append(named_trial(search,'Wider ten-flight plan for 331 and 332',wider,[DAY_BANK],retimings))
    # Bank width is an explicit hard constraint, even when five minutes would
    # resolve the otherwise feasible SYR gate/timing tradeoff.
    syr_plans=[{'route':331,'legs':[leg('BWI','SYR',395),leg('SYR','BWI',500)]}]
    change=make_overlay(search,syr_plans)
    change['hubBankChanges']=[{'bankId':'SYR-B2','expectedStartMinute':465,'expectedEndMinute':525,'startMinute':460}]
    change['bankAssignmentsToAdd'].append({'legId':change['insertLegs'][0]['id'],'operation':'arrival','bankId':'SYR-B2'})
    validation,_=validate(search,change)
    result.append({'name':'SYR morning with five-minute bank-start extension',
                   'plans':syr_plans,'bankChanges':change['hubBankChanges'],'validation':validation})
    # Earlier-finishing 331 sensitivity: bank and pairing/gate constraints still
    # apply when retiming the whole triangle, so do not treat it as a free fix.
    early_bank={'id':'DAY-B9','hub':'DAY','startMinute':1245,'endMinute':1305}
    early_plans=[phf,{'route':331,'legs':[leg('BWI','DAY',1168),leg('DAY','BWI',1300)]}]
    result.append(named_trial(search,'Earlier 331 ending with a 20:45 DAY bank',early_plans,[early_bank],
                              retime(search,331,[-8,-10,-24,-24,-24])))
    return result


def review_audit(search, selected):
    change=make_overlay(search,selected['plans'],selected['banks'],selected['retimings'])
    trial=apply_optimization_overlay(search.base,change)
    options=search.screen.enumerate(trial['legs']);loads,records=search.screen.allocate(options)
    changed=[]
    for r in change['retimeLegs']:
        old=search.legs[r['legId']];new=next(l for l in trial['legs'] if l['id']==old['id'])
        changed.append({'flight':old['flight'],'route':old['route'],'origin':old['origin'],'destination':old['destination'],
                        'oldDeparture':old['departure'],'oldArrival':clock(old['arrivalMinute']),
                        'newDeparture':new['departure'],'newArrival':clock(new['arrivalMinute']),
                        'shiftMinutes':new['departureMinute']-old['departureMinute'],
                        'oldLocal':search.screen.loads[old['id']]['local'],
                        'oldConnecting':sum(v for k,v in search.screen.loads[old['id']].items() if k!='local'),
                        'newLocal':loads[old['id']]['local'],
                        'newConnecting':sum(v for k,v in loads[old['id']].items() if k!='local')})
    slower=[];lost=[]
    for od,previous in search.screen.options.items():
        if not previous:continue
        now=options.get(od,[])
        if not now:lost.append({'origin':od[0],'destination':od[1],'od':search.screen.od[od[0]][od[1]]});continue
        before=min(c['elapsed'] for c in previous);after=min(c['elapsed'] for c in now)
        if after>before:
            slower.append({'origin':od[0],'destination':od[1],'od':search.screen.od[od[0]][od[1]],
                           'oldFastestMinutes':before,'newFastestMinutes':after,'differenceMinutes':after-before})
    selected['reviewAudit']={'retimedFlights':changed,'bankAssignmentReplacements':change['bankAssignmentReplacements'],
                             'marketsWithSlowerBestItinerary':sorted(slower,key=lambda r:-r['od']),
                             'marketsLosingAllConnections':lost}
    return change,trial


def save_proposal(search, report):
    selected=next(t for t in report['jointTrials'] if t['name']=='Strict minimum-turn DAY bank with CLT/SDF feeders')
    alternative=next(t for t in report['jointTrials'] if t['name']=='DAY turns and late-bank feeders; preserve every existing flight')
    change,trial=review_audit(search,selected)
    for choice in report['jointTrials']:
        if choice.get('demand') and choice is not selected:
            review_audit(search,choice)
    v=selected['validation']
    assert not v['operatingErrors'] and not v['hardStopFailures']
    assert all(v[k]=='pass' for k in ('structural','planning','overnight','gates'))
    change['id']='schedule-7-v1.2.3-bwi-round-1-proposal'
    change['schedule'].update(id='schedule_7_v1_2_3_draft',version='1.2.3',label='Schedule 7 v1.2.3 proposed draft; unpublished')
    change['approval']={'status':'proposed; not approved for publication','scope':'Two added Route 331 round trips, CLT/SDF late-DAY feeders, one DAY bank. All existing flights and Route 332 originator preserved.',
                        'userInstruction':'Begin work on v1.2.3; holistic schedule changes open as an option.',
                        'pendingDecisions':['Choose PHF or DAY morning turn on Route 331','DAY-B9 and two supporting feeders','Publication']}
    trial=apply_optimization_overlay(search.base,change)
    write_json(ROOT/'config/proposals/schedule_7_v1_2_3_round_1.json',change)
    write_json(ROOT/'data/schedules/schedule_7_v1_2_3_draft/canonical_schedule.json',trial)
    report['recommendation']={'primary':selected['name'],'alternative':alternative['name'],
        'status':'Proposed draft only; no release or manifest changes',
        'overlay':'config/proposals/schedule_7_v1_2_3_round_1.json',
        'canonical':'data/schedules/schedule_7_v1_2_3_draft/canonical_schedule.json',
        'baselineLegs':len(search.base['legs']),'draftLegs':len(trial['legs']),
        'newLegs':len(change['insertLegs']),'retimedLegs':len(change['retimeLegs']),
        'reason':'The PHF morning turn has the strongest connecting opportunity per block minute. The DAY morning alternative expands a new pairing. Preserve Route 332 because retiming its PHF feed harms BWI-BNA/PGD best journeys; preserve MCI-BWI because delaying it loses OKC/XNA connections.'}
    output=ROOT/'builds/schedule_7_v1_2_3_draft'
    for filename,data in {'canonical_schedule.json':trial,'validation_report.json':validate_schedule(trial),
        'operating_validation_report.json':validate_operating_rules(trial),
        'overnight_turn_validation.json':validate_overnight_turns(trial),'gates.json':export_gate_schedule(trial)}.items():
        write_json(output/filename,data)


def main():
    search=HoldSearch(read_json(ROOT/BASE))
    result={'workVersion':'1.2.3','status':'analysis-only; unpublished',
            'baseCanonical':BASE,'baseSha256':sha256_file(ROOT/BASE),'demandId':search.screen.demand_id,
            'interpretation':'Seat-uncapped relative-choice opportunities with all competing nonstops and one/two-stop itineraries. Not load forecasts or incremental passengers.',
            'morning331':morning(search,331),'morning332':morning(search,332),
            'eveningDayReturn':evening_day(search,False),'eveningDayOvernight':evening_day(search,True),
            'alternatives':alternatives(search),'dayFeederScreen':day_feeders(search),
            'jointTrials':joint_trials(search)}
    save_proposal(search,result)
    write_json(ROOT/REPORT,result)
    print(REPORT,flush=True)


if __name__=='__main__':main()
