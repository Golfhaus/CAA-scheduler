"""Rescreen hub exchanges with all added terminators arriving by 00:01 local."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import analyze_schedule_7_v1_2_4_hub_swaps as engine
from caa_scheduler.io import read_json,write_json
OUT='config/proposals/schedule_7_v1_2_4_00_01_swaps_review.json'
CUTOFF=1441
original_direction=engine.direction

def direction(s,a,b):
    x=original_direction(s,a,b)
    rejected=[t for t in x['timings'] if t['leg']['arrivalMinute']>CUTOFF]
    x['timings']=[t for t in x['timings'] if t['leg']['arrivalMinute']<=CUTOFF]
    if rejected:x['rejectCounts']['arrival after user 00:01 cutoff']=len(rejected)
    # Include the exact cutoff boundary, even when it lies off the five-minute
    # grid. This is important for borderline reciprocal west-to-east legs.
    dep=CUTOFF-s.leg(a['terminator'],b['terminator'],0,a['fleet'])['arrivalMinute']
    if (x['existingFrequency']<6 and x['earliestDeparture']<=dep<=x['latestDeparture']
        and all(t['leg']['departureMinute']!=dep for t in x['timings'])):
        leg=s.leg(a['terminator'],b['terminator'],dep,a['fleet'])
        ron=1440+b['nextOriginator']['departureMinute']-leg['arrivalMinute']
        if ron>=40 and s.spacing([leg]):
            missing=[{'hub':hub,'operation':op,'minute':minute%1440,'clock':engine.clock(minute)}
                     for op,hub,minute in [('departure',leg['origin'],dep),('arrival',leg['destination'],leg['arrivalMinute'])]
                     if s.bank(hub,minute) is None]
            x['timings'].append({'leg':leg,'missingBanks':missing,'strict':not missing,'score':engine.fast_score(s,leg),'ronMinutes':ron})
    x['timings'].sort(key=lambda t:(len(t['missingBanks']),-t['score'],t['leg']['departureMinute']))
    x['latestArrivalMinute']=CUTOFF
    return x

def main():
    engine.OUT=OUT;engine.direction=direction
    engine.screen()
    r=read_json(ROOT/OUT)
    r['status']='00:01 local cutoff review only; accepted flying and banks unchanged.'
    r['scope']='The same 29 eligible hub terminators and 97 matching-fleet reciprocal pairs. Every added leg must arrive no later than 00:01 local on the next calendar day. Existing clocks retained.'
    r['arrivalCutoffMinute']=CUTOFF
    for q in r['pairs']:
        if 'originalPairId' not in q:
            q['originalPairId']=q['id'];q['id']='MID-'+q['id']
    write_json(ROOT/OUT,r)
    engine.prove_lines()
    engine.coordinated()
    engine.validate_candidates()
    r=read_json(ROOT/OUT)
    for q in r['pairs']+r.get('coordinatedCandidates',[]):
        for f in q.get('demand',{}).get('flights',[]):assert f['arrivalMinute']<=CUTOFF
    print('MIDNIGHT COUNTS',r['counts'],r.get('coordinatedSearch'),flush=True)

if __name__=='__main__':main()
