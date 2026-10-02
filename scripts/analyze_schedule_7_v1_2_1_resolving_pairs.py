"""Read-only aircraft availability screen for directional coverage remedies.

All trial overlays stay in memory. No schedule/configuration is written.
"""
from collections import defaultdict, Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_1_directional_coverage import clock, normalize, largest_gap
from analyze_schedule_7_v1_2_1_remaining_holds import baseline
from build_schedule_7_v1_2_1_remaining_holds import OVERLAY
from caa_scheduler.io import read_json, write_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.gates import GateCapacityError, build_claims, split_for_waypoint, apply_forced_stand_splits
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot

PAIRS = [('SAT','MCI'), ('JAN','MCI'), ('CAE','PHF'), ('PIT','SYR')]


def windows(schedule):
    grouped = defaultdict(list)
    for leg in schedule['legs']:
        grouped[leg['route']].append(leg)
    for sequence in grouped.values():
        sequence.sort(key=lambda l: l['sequenceWithinRoute'])
    next_starts = {}
    lines = defaultdict(list)
    for route, sequence in grouped.items():
        lines[sequence[0]['line']].append((sequence[0]['day'], route))
    for items in lines.values():
        items.sort()
        for (_, route), (_, following) in zip(items, items[1:] + items[:1]):
            next_starts[route] = grouped[following][0]
    result = []
    for route, sequence in sorted(grouped.items()):
        first,last = sequence[0], sequence[-1]
        common = {k:first[k] for k in ('route','fleet','line','day')}
        result.append({**common,'type':'Late originator','city':first['origin'],
                       'start':270,'end':normalize(first['departureMinute']),
                       'earliest':270,'deadline':normalize(first['departureMinute'])-40})
        next_first = next_starts[route]
        assert next_first['origin'] == last['destination']
        end = min(1620, normalize(next_first['departureMinute'])+1440-40)
        result.append({**common,'type':'Early terminator','city':last['destination'],
                       'start':normalize(last['arrivalMinute']),'end':end,
                       'earliest':normalize(last['arrivalMinute'])+40,'deadline':end})
        for before,after in zip(sequence, sequence[1:]):
            start,end=normalize(before['arrivalMinute']),normalize(after['departureMinute'])
            result.append({**common,'type':'Hold','city':before['destination'],
                           'start':start,'end':end,'earliest':start+40,'deadline':end-40,
                           'before':before['id'],'after':after['id']})
    return result


def points(search, a,b,start,end,fleet):
    delta=search.leg(a,b,0,fleet)['arrivalMinute']
    values=set(search.grid(start,end))
    # Include exact bank boundaries, even if they fall off the five-minute grid.
    for bank in search.base['hubBanks']:
        for boundary in (bank['startMinute'],bank['endMinute']-1):
            if bank['hub']==a:values.add(boundary)
            if bank['hub']==b:values.add(boundary-delta)
    return sorted(x for x in values if start<=x<=end)


def validate(search, selection):
    trial=apply_optimization_overlay(search.base, search.overlay(selection))
    originals={l['id']:l for l in trial['legs']}
    for leg in search.base['legs']:
        assert all(originals[leg['id']][key]==leg[key] for key in (
            'flight','route','line','day','fleet','origin','destination','departureMinute','arrivalMinute'))
    structural=validate_schedule(trial)
    operating=validate_operating_rules(trial)
    overnight=validate_overnight_turns(trial)
    reasons=[c['id'] for c in operating['checks'] if c['hardStop'] and c['status']=='fail']
    if operating['summary']['effectiveErrorFindings']:
        reasons.extend(c['id'] for c in operating['checks'] if c['severity']=='error' and c['status']=='fail')
    if structural['status']!='pass':reasons.append('structural')
    if overnight['status']!='pass':reasons.append('overnight')
    if not reasons:
        try:
            export_gate_schedule(trial)
        except GateCapacityError:
            reasons.append('physical_gate_capacity')
    if not reasons:
        planning=validate_planning_snapshot(reconstruct_planning_snapshot(trial),trial)
        if planning['status']!='pass':reasons.append('planning')
    return trial, sorted(set(reasons)), operating


def minimum_touches(search):
    """A sound gate-only lower bound; parking middles can use stands."""
    result={}
    for city in search.base['cities']:
        code=city['code'];counts=[0]*1440
        claims=build_claims(search.base['legs'],code,cyclic_successor_holds=True)
        forced=search.base['gatePlan'].get('forcedStandSplits',{}).get(code,[])
        if forced:claims=apply_forced_stand_splits(claims,set(forced))
        for claim in claims:
            if claim.kind=='forced_stand_mid':continue
            pieces=(claim,) if claim.end-claim.start<=150 else (split_for_waypoint(claim)[0],split_for_waypoint(claim)[2])
            for piece in pieces:search.mark(counts,piece.start,piece.end,1)
        result[code]=counts
    return result


def main():
    base=apply_optimization_overlay(baseline(),read_json(ROOT/OVERLAY))
    search=HoldSearch(base)
    touches=minimum_touches(search)
    inventory=[]; families=defaultdict(list)
    limits=base['operatingPolicy']['departureWindows']
    for window in windows(base):
        for spoke,hub in PAIRS:
            if window['city'] not in (spoke,hub):continue
            a=window['city'];b=hub if a==spoke else spoke
            fleet=window['fleet'];block=search.screen.utc(search.leg(a,b,0,fleet))[2]
            required=2*block+40
            duration=window['deadline']-window['earliest']
            item={**window,'pairing':f'{spoke}-{hub}', 'blockMinutes':block,
                  'slackMinutes':duration-required,'bankCompatibleTimings':0,
                  'spacingCompatibleTimings':0,'mandatoryGateRejections':0}
            inventory.append(item)
            if duration<required:continue
            max_a=limits['hubOrFocusLatestMinute'] if a in search.screen.hubs else limits['destinationLatestMinute']
            max_b=limits['hubOrFocusLatestMinute'] if b in search.screen.hubs else limits['destinationLatestMinute']
            for dep in points(search,a,b,window['earliest'],min(max_a,window['deadline']-required),fleet):
                out=search.leg(a,b,dep,fleet)
                if search.bank(a,dep) is None or search.bank(b,out['arrivalMinute']) is None:continue
                shift=search.leg(b,a,0,fleet)['arrivalMinute']
                for ret in points(search,b,a,out['arrivalMinute']+40,
                                  min(max_b,out['arrivalMinute']+240,window['deadline']-shift),fleet):
                    back=search.leg(b,a,ret,fleet)
                    if search.bank(b,ret) is None or search.bank(a,back['arrivalMinute']) is None:continue
                    item['bankCompatibleTimings']+=1
                    added=[out,back]
                    if not search.spacing(added):continue
                    item['spacingCompatibleTimings']+=1
                    intervals=[(out['arrivalMinute'],ret)] if ret-out['arrivalMinute']<=150 else [
                        (out['arrivalMinute'],out['arrivalMinute']+45),(ret-60,ret)]
                    if any(touches[b][t%1440]>=search.gate_capacity[b] for lo,hi in intervals for t in range(lo,hi)):
                        item['mandatoryGateRejections']+=1
                        continue
                    # Identify whether this fixes a primary audited gap or a secondary interval.
                    primary=any(largest_gap([normalize(t) for t in search.pairs[l['origin'],l['destination']]])[0]
                                < l['departureMinute'] <
                                largest_gap([normalize(t) for t in search.pairs[l['origin'],l['destination']]])[1]
                                for l in added)
                    score,values=search.score(added)
                    families[window['route'],a,b,window['type'],window['start']].append(
                        {**window,'pairing':f'{spoke}-{hub}','legs':added,'score':score,'legScores':values,
                         'primaryGapRemedy':primary})
    results=[]
    for key,candidates in sorted(families.items()):
        print('CHECKING',key,'timings',len(candidates),flush=True)
        rejected=Counter();success=None
        for candidate in sorted(candidates,key=lambda x:-x['score']):
            trial,reasons,operating=validate(search,{candidate['route']:candidate})
            if reasons:
                rejected.update(reasons)
                continue
            success=candidate
            ids={l['id'] for l in base['legs']}
            added=[l for l in trial['legs'] if l['id'] not in ids]
            loads,records=search.screen.allocate(search.screen.enumerate(trial['legs']))
            success['proposedFlights']=[{**l,'opportunity':dict(loads[l['id']]),
                'totalOpportunity':sum(loads[l['id']].values()),
                'connections':records[l['id']]} for l in added]
            success['validation']={'effectiveErrors':operating['summary']['effectiveErrorFindings'],
                                   'structural':'pass','overnight':'pass','planning':'pass','phos':0}
            break
        results.append({'family':list(key),'timings':len(candidates),'rejections':dict(rejected),'best':success})
        print('FAMILY',key,'timings',len(candidates),'rejected',dict(rejected),'BEST',
              [(l['origin'],l['destination'],clock(l['departureMinute']),clock(l['arrivalMinute']),round(sum(l['opportunity'].values()),1))
               for l in success['proposedFlights']] if success else None,flush=True)
    # Independently validated choices can still conflict when proposed together.
    selected={}
    for result in results:
        best=result['best']
        if best and (best['route'] not in selected or best['score']>selected[best['route']]['score']):
            selected[best['route']]=best
    combined,reasons,operating=validate(search,selected) if selected else (None,[],None)
    report={'baseline':base['schedule']['id'],'baselineRoutes':len({l['route'] for l in base['legs']}),
            'baselineLegs':len(base['legs']),'pairs':[list(p) for p in PAIRS],
            'inventory':inventory,'results':results,'jointValidationReasons':reasons,
            'method':'No retiming; same endpoints and fleet; normal departure windows; five-minute grid plus exact bank boundaries; destination turns 40–240 minutes; fixed banks/gates/stands; 40-minute minimum turns; full one/two-stop uncapped relative-choice model. Each demand result is an isolated addition; joint feasibility also checked.'}
    write_json(ROOT/'builds/schedule_7_v1_2_1_resolving_pairs.json',report)
    print('JOINT',reasons,flush=True)


if __name__=='__main__':main()
