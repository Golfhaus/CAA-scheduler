"""Unpublished JAX evening-bank aircraft and connection screen.

Store approved SFB extensions separately from proposed bank/feeder flying.
All candidate schedule overlays remain in memory; no release assets change.
"""
from collections import defaultdict, Counter
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_2_sfb_evenings import overlay, clock
from caa_scheduler.io import read_json, write_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.gates import GateCapacityError
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.bank_placement import TIMEZONE_OFFSETS

PLAN = ROOT / 'config/proposals/schedule_7_v1_2_2_sfb_extensions.json'
REPORT = ROOT / 'config/proposals/schedule_7_v1_2_2_jax_bank_screen.json'
BANK = {'id': 'JAX-B15', 'hub': 'JAX', 'startMinute': 1245, 'endMinute': 1305}


def check(search, plans, retimings=None):
    changes = overlay(search, plans)
    changes['retimeLegs'] = retimings or []
    trial = apply_optimization_overlay(search.base, changes)
    retimed_ids = {r['legId'] for r in changes['retimeLegs']}
    old = {leg['id']: leg for leg in search.base['legs']}
    for leg in trial['legs']:
        if leg['id'] in old:
            fields = ('flight', 'route', 'line', 'day', 'fleet', 'origin', 'destination')
            if leg['id'] not in retimed_ids:
                fields += ('departureMinute', 'arrivalMinute')
            assert all(leg[k] == old[leg['id']][k] for k in fields)
    op = validate_operating_rules(trial)
    overnight = validate_overnight_turns(trial)
    result = {'structural': validate_schedule(trial)['status'],
              'operatingErrors': op['summary']['effectiveErrorFindings'],
              'hardStopFailures': [c['id'] for c in op['checks'] if c['hardStop'] and c['status'] == 'fail'],
              'blocking': [{'check': c['id'], 'findings': c['findings']} for c in op['checks']
                           if c['severity'] == 'error' and c['status'] == 'fail'],
              'overnight': overnight['status'], 'overnightFindings': overnight['findings'],
              'planning': validate_planning_snapshot(reconstruct_planning_snapshot(trial), trial)['status']}
    try:
        gates = export_gate_schedule(trial)
        result['gates'] = 'pass'
        result['jax'] = {k: v for k, v in next(c for c in gates['cities'] if c['code'] == 'JAX').items() if k != 'claims'}
        stands = [x for c in gates['cities'] for x in c['claims'] if x['rowType'] == 'stand']
        result['standClaims'] = len(stands)
        result['standMinutes'] = sum(x['end'] - x['start'] for x in stands)
    except GateCapacityError as exc:
        result['gates'] = 'fail'
        result['gateFailure'] = str(exc)
    return result, trial


def details(search, trial, identifiers):
    options = search.screen.enumerate(trial['legs'])
    loads, records = search.screen.allocate(options)
    result = []
    for leg in trial['legs']:
        if leg['id'] not in identifiers:
            continue
        markets = Counter()
        groups = Counter()
        for r in records[leg['id']]:
            if r['stops']:
                markets[r['origin'], r['destination']] += r['opportunity']
                other = r['destination'] if leg['destination'] == 'JAX' else r['origin']
                groups[search.screen.cities[other]['group']] += r['opportunity']
        result.append({**leg, 'departureClock': clock(leg['departureMinute']),
                       'arrivalClock': clock(leg['arrivalMinute']),
                       'local': loads[leg['id']]['local'],
                       'connecting': sum(v for k, v in loads[leg['id']].items() if k != 'local'),
                       'oneStop': sum(r['opportunity'] for r in records[leg['id']] if r['stops'] == 1),
                       'twoStop': sum(r['opportunity'] for r in records[leg['id']] if r['stops'] == 2),
                       'groups': dict(groups),
                       'topMarkets': [{'origin': a, 'destination': b, 'opportunity': v}
                                      for (a, b), v in markets.most_common(8)]})
    return result


def buffered_pie(search, joint_plans, overnight_choice, inherited_ids):
    plans = deepcopy(overnight_choice['plans'])
    plans[1]['legs'][0] = search.leg('JAX', 'PIE', 360, 'CRJ900')
    all_plans = joint_plans + plans
    validation, trial = check(search, all_plans)
    ids = {l['id'] for l in trial['legs']} - set(search.legs)
    ids.update(inherited_ids)
    return {'plans': plans, 'validation': validation, 'demand': details(search, trial, ids),
            'rationale': '06:00 JAX departure reaches PIE at 06:54, leaving 61 minutes before Route 515 at 07:55, instead of the 41-minute ground time from the demand-optimal 06:20 departure.'}


def retimed_pie(search, joint_plans, overnight_choice, inherited_ids):
    first_two = sorted((l for l in search.base['legs'] if l['route'] == 515),
                       key=lambda l: l['sequenceWithinRoute'])[:2]
    retimings = [{'legId': l['id'], 'expectedDepartureMinute': l['departureMinute'],
                  'expectedArrivalMinute': l['arrivalMinute'],
                  'departureMinute': l['departureMinute'] + 9,
                  'arrivalMinute': l['arrivalMinute'] + 9} for l in first_two]
    validation, trial = check(search, joint_plans + overnight_choice['plans'], retimings)
    ids = {l['id'] for l in trial['legs']} - set(search.legs)
    ids.update(inherited_ids)
    return {'status': 'optional retiming proposal; not approved', 'retimeLegs': retimings,
            'validation': validation, 'demand': details(search, trial, ids),
            'rationale': 'Keep the 06:20 JAX departure to capture the 05:50 RDU and TYS arrivals. Move Route 515 PIE–SYR and SYR–PIE nine minutes later, giving 50 minutes at PIE. SYR departure is 11:29, just inside Bank 3 ending at 11:30. A 15-minute shift fails that bank. The 16:05 PIE–SYR and remaining flights stay unchanged.'}


def main():
    base = read_json(ROOT / 'data/schedules/schedule_7_v1_2_1/canonical_schedule.json')
    original = HoldSearch(base)
    accepted = [{'route': 702, 'legs': [original.leg('SFB', 'JAX', 1205, 'MAX9'), original.leg('JAX', 'SFB', 1293, 'MAX9')]},
                {'route': 704, 'legs': [original.leg('SFB', 'BHM', 1219, 'MAX9'), original.leg('BHM', 'SFB', 1395, 'MAX9')]}]
    saved = overlay(original, accepted)
    saved['id'] = 'schedule-7-v1.2.2-approved-sfb-extensions'
    saved['schedule'].update(id='schedule_7_v1_2_2_draft', version='1.2.2',
                             label='Schedule 7 v1.2.2 unpublished plan', status='draft')
    saved['approval'] = {'status': 'approved-for-plan', 'scope': 'Both SFB extensions only; publication reserved to user',
                         'instruction': 'Store both the BHM and JAX extensions.', 'date': '2026-10-03'}
    saved['pendingDecisions'] = ['JAX late-bank timing and bank-count policy', 'Additional feeders and overnight originators', 'Publication']
    saved['bankAssignmentsToAdd'] = []  # No existing bank fits; finalize with selected late bank.
    write_json(PLAN, saved)

    bank_overlay = {'baseSchedule': {'scheduleId': base['schedule']['id']},
                    'id': 'v1.2.2-jax-late-bank-trial',
                    'schedule': {'id': 'schedule_7_v1_2_2_jax_bank_trial', 'version': '1.2.2-analysis',
                                 'label': 'Unpublished JAX evening-bank trial', 'status': 'draft'},
                    'hubBanksToAdd': [BANK], 'hubBankCountOverrides': {'JAX': 15}}
    bank_base = apply_optimization_overlay(base, bank_overlay)
    bank_search = HoldSearch(bank_base)
    accepted_validation, draft = check(bank_search, accepted)
    search = HoldSearch(draft)
    routes = defaultdict(list)
    lines = defaultdict(list)
    for leg in draft['legs']:
        routes[leg['route']].append(leg)
    for sequence in routes.values():
        sequence.sort(key=lambda l: l['sequenceWithinRoute'])
        lines[sequence[0]['line']].append(sequence)
    successors = {}
    for sequences in lines.values():
        sequences.sort(key=lambda ls: ls[0]['day'])
        for current, following in zip(sequences, sequences[1:] + sequences[:1]):
            successors[current[0]['route']] = following[0]
    inventory, screened = [], []
    for route, sequence in sorted(routes.items()):
        first, last = sequence[0], sequence[-1]
        city, fleet = last['destination'], first['fleet']
        if search.screen.cities[city]['group'] not in ('CGI', 'FLP', 'GCP', 'APP') or route in (702, 704):
            continue
        # Unwrap the entire aircraft day in UTC, including red-eyes arriving
        # after the next day's 04:30 originator floor. Clock sorting alone
        # incorrectly presents those arrivals as unused daytime aircraft.
        previous_arrival = None
        for leg in sequence:
            dep, _, block = search.screen.utc(leg)
            if previous_arrival is not None:
                while dep < previous_arrival:
                    dep += 1440
            previous_arrival = dep + block
        finish = previous_arrival + TIMEZONE_OFFSETS[search.screen.cities[city]['timezone']]
        if finish >= 1260:
            continue
        following = successors[route]
        offset = search.leg(city, 'JAX', 0, fleet)['arrivalMinute']
        back_offset = search.leg('JAX', city, 0, fleet)['arrivalMinute']
        earliest_arrival = finish + 40 + offset
        latest_morning = following['departureMinute'] - 40 - back_offset
        item = {'route': route, 'line': first['line'], 'day': first['day'], 'fleet': fleet,
                'city': city, 'group': search.screen.cities[city]['group'], 'finish': clock(finish),
                'redEyeTerminator': finish < 390, 'earliestJaxArrival': clock(earliest_arrival),
                'nextRoute': following['route'], 'nextStart': following['departure'],
                'latestMorningJaxDeparture': clock(latest_morning), 'overnightPossible': latest_morning >= 270,
                'blockMinutes': search.screen.utc(search.leg(city, 'JAX', 0, fleet))[2],
                'currentFrequencyToJax': len(search.pairs[city, 'JAX']),
                'currentFrequencyFromJax': len(search.pairs['JAX', city]),
                'localOdBothDirections': search.screen.od[city]['JAX'] + search.screen.od['JAX'][city]}
        inventory.append(item)
        for kind in ('evening-return', 'jax-overnight'):
            candidates = []
            if kind == 'jax-overnight' and latest_morning < 270:
                continue
            for arrival in sorted({*range(1245, 1305, 5), 1253, 1263, 1274, earliest_arrival}):
                if not 1245 <= arrival < 1305:
                    continue
                departure = arrival - offset
                if departure < finish + 40 or departure > 1260:
                    continue
                inbound = search.leg(city, 'JAX', departure, fleet)
                returns = (sorted({1293, 1300, 1304, arrival + 40}) if kind == 'evening-return'
                           else search.grid(270, latest_morning))
                for returning in returns:
                    if kind == 'evening-return' and (returning < arrival + 40 or returning >= 1305):
                        continue
                    if search.bank('JAX', returning) is None:
                        continue
                    outbound = search.leg('JAX', city, returning, fleet)
                    if not search.spacing([inbound, outbound]):
                        continue
                    plans = [{'route': route, 'legs': [inbound]}]
                    if kind == 'evening-return':
                        plans[0]['legs'].append(outbound)
                    else:
                        plans.append({'route': following['route'], 'legs': [outbound]})
                    score, values = search.score([inbound, outbound])
                    candidates.append({'plans': plans, 'score': score, 'legScores': values})
            candidates.sort(key=lambda c: -c['score'])
            for candidate in candidates[:8]:
                validation, trial = check(search, candidate['plans'])
                if (validation['operatingErrors'] or validation['hardStopFailures'] or
                        any(validation[k] != 'pass' for k in ('structural', 'planning', 'overnight', 'gates'))):
                    continue
                ids = {l['id'] for l in trial['legs']} - set(search.legs)
                screened.append({**item, 'kind': kind, **candidate, 'validation': validation,
                                 'demand': details(search, trial, ids)})
                break
    # One aircraft per city where alternatives exist. Overnight options are separately reviewed.
    selected = []
    for city in ('MSY', 'SAV', 'CLT', 'ROA', 'MLB'):
        choices = [r for r in screened if r['city'] == city and r['kind'] == 'evening-return']
        if choices:
            selected.append(max(choices, key=lambda r: r['score']))
    joint_plans = [p for r in selected for p in r['plans']]
    joint_validation, joint = check(search, joint_plans)
    new_ids = {l['id'] for l in joint['legs']} - set(search.legs)
    # Include approved SFB legs to measure the late bank's effect on those connections too.
    new_ids.update(l['id'] for l in draft['legs'] if l['id'] not in original.legs)
    joint_demand = details(search, joint, new_ids)
    # Test the most useful overnight candidate with the evening-return bank.
    overnight_choice = next((r for r in screened if r['route'] == 514 and r['kind'] == 'jax-overnight'), None)
    overnight_joint = None
    if overnight_choice:
        combined_plans = joint_plans + overnight_choice['plans']
        combined_validation, combined_trial = check(search, combined_plans)
        combined_ids = {l['id'] for l in combined_trial['legs']} - set(search.legs)
        combined_ids.update(new_ids)
        overnight_joint = {'routes': [r['route'] for r in selected] + [514, 515],
                           'validation': combined_validation,
                           'demand': details(search, combined_trial, combined_ids)}
    report = {'workVersion': '1.2.2', 'status': 'analysis-only; unpublished',
              'baseline': base['schedule']['id'], 'demandId': search.screen.demand_id,
              'interpretation': 'Full-capture seat-uncapped relative-choice opportunity units, not passenger forecasts or net incremental demand. Existing alternatives included. Main screen preserves all existing flight clocks and identities; optional Route 515 retiming sensitivity is explicitly separate.',
              'draftBank': {**BANK, 'startClock': clock(1245), 'endClockExclusive': clock(1305), 'status': 'proposed; not finalized'},
              'approvedExtensionsValidationWithProposedBank': accepted_validation,
              'inventory': inventory, 'candidates': screened,
              'jointEveningReturnScreen': {'routes': [r['route'] for r in selected], 'plans': joint_plans,
                                           'validation': joint_validation, 'demand': joint_demand},
              'jointWithPieOvernight': overnight_joint,
              'jointWithBufferedPieOvernight': buffered_pie(search, joint_plans, overnight_choice, new_ids) if overnight_choice else None,
              'jointWithRetimedPieSuccessor': retimed_pie(search, joint_plans, overnight_choice, new_ids) if overnight_choice else None,
              'recommendedBankScenario': retimed_pie(search, [p for p in joint_plans if p['route'] in (341, 504, 338)], overnight_choice, new_ids) if overnight_choice else None,
              'recommendations': {'highestPriorityEveningReturns': [341, 504, 338],
                                  'alternateForClt': 340, 'conditionalOvernight': [514, 515],
                                  'marginal': [114], 'defer': [126, 307, 308],
                                  'optionalRetiming': 'Route 515 first two existing flights +9 minutes; subject to user decision',
                                  'publication': 'reserved to user'},
              'notes': ['Red-eye finish times describe aircraft availability, not availability of the same crew.',
                        'Overnight candidates add the morning return to the cyclic successor route; do not leave its original first departure without an aircraft.',
                        'Single-candidate inbound demand is limited by existing late departures. Joint bank analysis includes connections between new flights.',
                        'All feeder flying and bank policy remain proposed; only the SFB extensions have been accepted for storage.']}
    write_json(REPORT, report)
    for r in screened:
        print(r['route'], r['city'], r['fleet'], r['kind'],
              [(l['departureClock'], l['arrivalClock'], round(l['local'], 1), round(l['connecting'], 1)) for l in r['demand']])
    print('JOINT', joint_validation)
    for l in joint_demand:
        print(l['route'], l['origin'], l['destination'], l['departureClock'], l['arrivalClock'],
              round(l['local'], 1), round(l['connecting'], 1), l['groups'])


if __name__ == '__main__':
    main()
