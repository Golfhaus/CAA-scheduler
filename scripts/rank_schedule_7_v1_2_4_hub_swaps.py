"""Recommend a compatible hub-swap portfolio. All outputs are analysis only."""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from caa_scheduler.io import read_json,write_json,sha256_file
from caa_scheduler.operating_validation import validate_operating_rules
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import validate,demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4 import cache_network
from analyze_schedule_7_v1_2_4_xna import maintenance
BASE='data/schedules/schedule_7_v1_2_4_round_4/canonical_schedule.json'
REVIEW='config/proposals/schedule_7_v1_2_4_hub_swaps_review.json'
OUT='config/proposals/schedule_7_v1_2_4_hub_swaps_priorities.json'

def combine(base,review,ids):
    qs={q['id']:q for q in review['pairs']+review.get('coordinatedCandidates',[])}
    parts=[read_json(ROOT/qs[x]['overlay']) for x in ids]
    c=deepcopy(parts[0])
    for key in ('routeReassignments','hubBanksToAdd','insertLegs','bankAssignmentsToAdd'):
        c[key]=[deepcopy(x) for p in parts for x in p.get(key,[])]
    assert len({x['sourceRoute'] for x in c['routeReassignments']})==len(c['routeReassignments'])
    c['hubBankCountOverrides']={h:base['operatingPolicy']['hubBankCounts'][h]+sum(b['hub']==h for b in c['hubBanksToAdd']) for h in {b['hub'] for b in c['hubBanksToAdd']}}
    name='__'.join(ids)
    c['id']='schedule-7-v1.2.4-hub-swap-portfolio-'+name
    c['schedule'].update(id='schedule_7_v1_2_4_recommended_swaps_'+name,version='1.2.4-analysis',label='Recommended hub swaps; analysis only')
    c['approval']={'status':'recommendation only; not approved for draft implementation or publication',
        'scope':'Explicit bank additions, reciprocal legs and full line reconstruction. Existing flight clocks retained.',
        'publication':'Reserved to user decision'}
    return c

def evaluate(s,review,ids):
    c=combine(s.base,review,ids)
    v,t=validate(s,c)
    assert good(v),v
    inserted={x['id'] for x in c['insertLegs']}
    old={x['id']:x for x in s.base['legs']};now={x['id']:x for x in t['legs']}
    keys=('flight','pairing','fleet','origin','destination','departureMinute','arrivalMinute')
    assert all(all(now[k][f]==l[f] for f in keys) for k,l in old.items())
    assert len(now)==len(old)+len(inserted)
    assert t['schedule']['fleetCounts']==s.base['schedule']['fleetCounts']
    labels={x['line'] for x in c['routeReassignments']}
    lengths={line:len({l['day'] for l in t['legs'] if l['line']==line}) for line in labels}
    assert all(9<=n<=12 for n in lengths.values())
    result={'options':ids,'validation':v,'lineLengths':lengths,'maintenance':{line:maintenance(t,line) for line in sorted(labels)},
            'banks':c['hubBanksToAdd'],'demand':demand(s,t,inserted),'connectionAudit':audit(s,t)}
    options=s.screen.enumerate(t['legs']);loads,records=s.screen.allocate(options)
    new=[];faster=[]
    for od,choices in options.items():
        if not choices:continue
        before=s.screen.options.get(od,[])
        if not before:new.append({'origin':od[0],'destination':od[1],'od':s.screen.od[od[0]][od[1]]})
        elif min(x['elapsed'] for x in choices)<min(x['elapsed'] for x in before):
            faster.append({'origin':od[0],'destination':od[1],'od':s.screen.od[od[0]][od[1]],
                           'oldMinutes':min(x['elapsed'] for x in before),'newMinutes':min(x['elapsed'] for x in choices)})
    result['newConnectedMarkets']=sorted(new,key=lambda x:-x['od'])
    result['fasterMarkets']=sorted(faster,key=lambda x:-x['od'])
    for f in result['demand']['flights']:
        feeders=set();onward=set();src=Counter();dst=Counter()
        for r in records[f['id']]:
            index=r['legs'].index(f['id'])
            if index:feeders.add(r['legs'][index-1])
            if index+1<len(r['legs']):onward.add(r['legs'][index+1])
            src[s.screen.cities[r['origin']]['group']]+=r['opportunity'];dst[s.screen.cities[r['destination']]['group']]+=r['opportunity']
        f['feederFlightCount']=len(feeders);f['onwardFlightCount']=len(onward);f['originGroups']=dict(src);f['destinationGroups']=dict(dst)
    op={x['id']:x for x in validate_operating_rules(t)['checks']}
    baseop={x['id']:x for x in validate_operating_rules(s.base)['checks']}
    assert not op['section_26_pairing_spacing']['findings']
    before={x['id']:x['evidence'] for x in baseop['section_26_city_departure_gap']['findings']}
    after={x['id']:x['evidence'] for x in op['section_26_city_departure_gap']['findings']}
    assert set(after)<=set(before)
    assert all(max(g['minutes'] for g in x['excessiveGaps'])<=max(g['minutes'] for g in before[city]['excessiveGaps']) for city,x in after.items())
    result['section26']={'checkA':'pass','newCheckBFindings':0,'worsenedCheckBGaps':0}
    path='config/proposals/schedule_7_v1_2_4_hub_swap_portfolio_'+('__'.join(ids)).replace('-','_')+'.json'
    write_json(ROOT/path,c);result['overlay']=path
    print('PORTFOLIO',ids,'pass',lengths,'new markets',len(new),'new O-D',result['demand']['newlyConnectedMarketDemand'],
          'faster',len(faster),[(f['origin']+'-'+f['destination'],round(f['total'],1)) for f in result['demand']['flights']],flush=True)
    return result

def main():
    base=read_json(ROOT/BASE);review=read_json(ROOT/REVIEW)
    assert sha256_file(ROOT/BASE)==review['baseSha256']
    assert (ROOT/BASE).read_bytes()==(ROOT/'data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json').read_bytes()
    s=HoldSearch(base);cache_network(s)
    report=read_json(ROOT/OUT) if (ROOT/OUT).exists() else {'baseCanonical':BASE,'baseSha256':review['baseSha256'],
      'status':'Recommendations only. Accepted draft and main are unchanged.',
      'method':'Prioritize second directional departures on currently one-flight pairs. Compare full one/two-stop opportunities and distinct newly connected/faster markets. Jointly reallocate demand before choosing a compatible set. No synthetic weighted score or load-factor forecast.',
      'portfolios':[]}
    assert report['baseSha256']==sha256_file(ROOT/BASE)
    for ids in (['337-344','159-165'],['337-344','159-165','703-715']):
        if any(x['options']==ids for x in report['portfolios']):continue
        report['portfolios'].append(evaluate(s,review,ids));write_json(ROOT/OUT,report)
    report['recommendation']={
      'firstPriority':['337-344','159-165'],
      'optionalLater':['703-715'],
      'fallbackFor337_344':'314-345 if the 2h08 PHF overnight cannot support the required maintenance/crew plan. It has lower demand and requires another bank window.',
      'defer':['115-136__125-135'],
      'decline':['Other PHF-MCI alternatives once 337-344 is selected','703-708','703-722','CRJ900 exchanges without a proved line cover'],
      'rationale':'The two first-priority swaps upgrade PHF-MCI and MCI-SYR from one to two departures each way, have complementary geographic benefits, and pass together. The optional MAX9 adds a third DAY-MCI flight, but a much weaker return and little genuinely new market coverage make it secondary. AD adds fifth DAY-JAX flights and needs a weak JAX-DAY leg to support the package.'}
    write_json(ROOT/OUT,report)
    p=report['portfolios'][0]
    md=['# Schedule 7 v1.2.4: hub-swap priorities','','Pursue 337/344 (PHF–MCI, CRJ700) and 159/165 (MCI–SYR, CRJ200) together. Both directional pairs increase from one to two daily departures. The joint scenario is fully validated; none of its flying is implemented.','',
        '| Priority | Routes | Market | Separate-scenario opportunity by direction | Connection benefit |',
        '|---|---|---|---|---|',
        '| 1 | 337/344 | PHF–MCI | 90.1 / 130.1 | 51.3 daily underlying O-D across newly connected markets; 15 markets with faster best journeys. PHF arrivals feed SAT at MCI, and the return feeds seven PHF departures. |',
        '| 2 | 159/165 | MCI–SYR | 101.3 / 33.7 | 43.0 daily underlying O-D across newly connected markets; 13 faster markets. Strong NEC coverage, including ALB, HVN and SWF, plus SYR evening feeds into MCI. |',
        '| Optional later | 703/715 | DAY–MCI | 129.6 / 42.2 | Adds a third flight each way. Only 4.0 daily O-D across new markets in its standalone scenario. Demand and directional imbalance make this a secondary MAX9 use. |',
        '| Defer | 115/136 plus 125/135 | DAY–JAX and DAY–MCI | 13.1 / 97.2 and 131.1 / 37.8 | Four flights and four new bank windows. DAY–JAX already has four departures each way, and the JAX–DAY addition is weak. |','',
        'Opportunity is seat-uncapped relative-choice demand, not expected loads or incremental passengers. Newly connected O-D is the underlying demand of markets with no previous valid itinerary, not the opportunity assigned to the added flight. Faster-market counts describe best elapsed journeys.','',
        '## Preferred plan, demand reallocated jointly','',
        '| Original routes | Flight | Local departure | Local arrival | Local opportunity | Connecting opportunity | Total opportunity |',
        '|---|---|---|---|---:|---:|---:|']
    for f in p['demand']['flights']:
        source=337 if '-R337-' in f['id'] else 344 if '-R344-' in f['id'] else 159 if '-R159-' in f['id'] else 165
        paired=344 if source==337 else 337 if source==344 else 165 if source==159 else 159
        md.append(f"| {source}/{paired} | {f['origin']}–{f['destination']} | {f['departureClock']} | {f['arrivalClock']} | {f['local']:.1f} | {f['connecting']:.1f} | {f['total']:.1f} |")
    md+=['',f"Joint plan: {len(p['newConnectedMarkets'])} newly connected directional O-D markets, {p['demand']['newlyConnectedMarketDemand']:.1f}/day underlying O-D, and {len(p['fasterMarkets'])} markets with faster best journeys. These figures account for overlap and must replace sums of the separate scenario metrics.",'',
         'The preferred plan requires PHF 02:00–03:00, SYR 02:00–03:00 and MCI 00:00–01:00 bank windows. All four departures use existing departure banks. It retains existing flight clocks and fleet counts. New line lengths are 10/9/9/9 days for the CRJ700 pool and 10/9 for the CRJ200 pool. §2.6, gates/stands, overnight continuity, maintenance cadence and planning pass together with no new or worsened city-gap finding. No market loses all connections or gets a slower best journey.','',
         '337/344 leaves 2h08 at PHF before the next originator. The PHF–MCI arrival connects to SAT with 33 minutes, only three minutes over the minimum. This makes a maintenance-task/crew check and connection reliability material implementation checks. If PHF overnight work does not fit, prefer the lower-demand 314/345 alternative, not an additional overlapping PHF–MCI exchange.','',
         'Decline the other PHF–MCI alternatives after selecting 337/344: they duplicate the same second-flight opportunity. Decline MAX9 DAY–PHF swaps: they add fifth flights where the weaker direction has only roughly 11–14 opportunity. Leave CRJ900 exchanges unchanged until a compliant line reconstruction is proved.','',
         'The optional DAY–MCI MAX9 scenario was also tested jointly with the preferred plan. DAY–MCI opportunity becomes 122.3 and MCI–DAY 38.2. It adds only one further newly connected market (1.6 daily underlying O-D) and 15 further faster-best-journey markets. Prefer 703/715 over the demand-equivalent 703/712: it gives 50 more minutes at MCI before the next originator and needs fewer changed overnight handoffs. It is not included in the recommended first package.','',
         f"Input snapshot SHA-256: `{report['baseSha256']}`.",'']
    output=ROOT/'outputs/schedule_7_v1_2_4_hub_swaps/Hub_Swap_Priorities.md'
    output.write_text('\n'.join(md));print('RECOMMENDATION SAVED',output,flush=True)

if __name__=='__main__':main()
