"""Screen every route boundary for additive JAX overnight flying.

Use the accepted v1.2.2 draft. Preserve every existing flight, including each
original originator. Report missing banks explicitly; never fabricate approvals.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_2_jax_bank import check, details, clock
from caa_scheduler.bank_placement import TIMEZONE_OFFSETS
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay

BASE = 'data/schedules/schedule_7_v1_2_2_draft/canonical_schedule.json'
REPORT = 'config/proposals/schedule_7_v1_2_2_late_originators.json'


def route_finish(search, sequence):
    previous = None
    for leg in sequence:
        dep, _, block = search.screen.utc(leg)
        if previous is not None:
            while dep < previous:
                dep += 1440
        previous = dep + block
    return previous + TIMEZONE_OFFSETS[search.screen.cities[sequence[-1]['destination']]['timezone']]


def points(search, city, fleet, start, end, night):
    values = set(search.grid(start, end))
    shift = search.leg(city, 'JAX', 0, fleet)['arrivalMinute'] if night else search.leg('JAX', city, 0, fleet)['arrivalMinute']
    for bank in search.base['hubBanks']:
        for edge in (bank['startMinute'], bank['endMinute'] - 1):
            if night:
                if bank['hub'] == city:
                    values.add(edge)
                if bank['hub'] == 'JAX':
                    values.add(edge - shift)
            else:
                if bank['hub'] == 'JAX':
                    values.add(edge)
                if bank['hub'] == city:
                    values.add(edge - shift)
    # Include exact 30-minute connection thresholds, not just five-minute grids.
    if night:
        for leg in search.departures['JAX']:
            for wait in (30, 240):
                values.add(leg['departureMinute'] - wait - shift)
    else:
        for leg in search.arrivals['JAX']:
            values.add(leg['arrivalMinute'] + 30)
    return sorted(t for t in values if start <= t <= end)


def bank_requirements(search, plans):
    requirements = []
    for plan in plans:
        for leg in plan['legs']:
            for op, city, minute in [('departure', leg['origin'], leg['departureMinute']),
                                     ('arrival', leg['destination'], leg['arrivalMinute'])]:
                if city in search.base['operatingPolicy']['hubs'] and search.bank(city, minute) is None:
                    requirements.append({'city': city, 'operation': op, 'time': clock(minute),
                                         'minute': minute, 'route': plan['route']})
    return requirements


def simplify_validation(result):
    # Approved legacy exceptions are preserved in the canonical, but do not
    # obscure the new candidate's unresolved findings in this review report.
    result['blocking'] = [{'check': c['check'], 'findings': [f for f in c['findings'] if not f.get('override')]}
                          for c in result['blocking'] if any(not f.get('override') for f in c['findings'])]
    return result


def reviewable(result):
    if (result['hardStopFailures'] or
            any(result[k] != 'pass' for k in ('structural', 'planning', 'overnight', 'gates'))):
        return False
    for check_result in result['blocking']:
        if check_result['check'] == 'hub_bank_alignment':
            continue
        if check_result['check'] == 'tiered_service_minimums' and all(
                len(f['evidence'].get('connectedHubs', [])) > f['evidence'].get('hubCountCap', 999) and
                f['evidence'].get('totalFlights', 0) >= f['evidence'].get('minimumFlights', 999) and
                f['evidence'].get('hubOrFocusFlights', 0) >= f['evidence'].get('minimumFlights', 999)
                for f in check_result['findings']):
            continue  # Explicit conditional hub-count exception, never approved here.
        return False
    return True


def close_misses(search, report):
    """Optional predecessor retiming sensitivities; keep originators unchanged."""
    results = []
    for item in report['inventory']:
        deficit = item.get('eveningDepartureShortfallMinutes', 999)
        if item.get('morningShortfallMinutes') != 0 or not 0 < deficit <= 30:
            continue
        sequence = sorted((l for l in search.base['legs'] if l['route'] == item['previousRoute']),
                          key=lambda l: l['sequenceWithinRoute'])
        times, previous = [], None
        for leg in sequence:
            dep, _, block = search.screen.utc(leg)
            while previous is not None and dep < previous:
                dep += 1440
            times.append((dep, dep + block))
            previous = dep + block
        shifts = [0] * len(sequence)
        shifts[-1] = -deficit
        for index in range(len(sequence) - 2, -1, -1):
            shifts[index] = min(0, times[index + 1][0] + shifts[index + 1] - times[index][1] - 40)
        retimings = [{'legId': l['id'], 'expectedDepartureMinute': l['departureMinute'],
                      'expectedArrivalMinute': l['arrivalMinute'], 'departureMinute': l['departureMinute'] + shift,
                      'arrivalMinute': l['arrivalMinute'] + shift}
                     for l, shift in zip(sequence, shifts) if shift]
        base_change = {'id': 'late-originator-retiming-sensitivity',
                       'baseSchedule': {'scheduleId': search.base['schedule']['id']},
                       'schedule': {'id': 'v122-retiming-sensitivity', 'label': 'Unapproved retiming sensitivity', 'status': 'draft'},
                       'retimeLegs': retimings}
        shifted = apply_optimization_overlay(search.base, base_change)
        shifted_search = HoldSearch(shifted)
        first = next(l for l in search.base['legs'] if l['route'] == item['originatorRoute'] and l['sequenceWithinRoute'] == 1)
        city, fleet = item['city'], item['fleet']
        inbound = search.leg(city, 'JAX', 1260, fleet)
        latest = first['departureMinute'] - 40 - search.leg('JAX', city, 0, fleet)['arrivalMinute']
        choices = []
        for dep in points(shifted_search, city, fleet, 270, latest, False):
            outbound = search.leg('JAX', city, dep, fleet)
            if not shifted_search.spacing([inbound, outbound]):
                continue
            plans = [{'route': item['previousRoute'], 'legs': [inbound]},
                     {'route': item['originatorRoute'], 'legs': [outbound]}]
            score, values = shifted_search.score([inbound, outbound])
            choices.append({'plans': plans, 'score': score, 'legScores': values,
                            'bankRequirements': bank_requirements(shifted_search, plans),
                            'morningGroundMinutes': first['departureMinute'] - outbound['arrivalMinute']})
        choices.sort(key=lambda c: (len(c['bankRequirements']), -c['score']))
        result = {**item, 'status': 'optional predecessor retiming; not approved', 'retimeLegs': retimings,
                  'maximumShiftMinutes': max(abs(x) for x in shifts), 'timingChoicesAfterRetime': len(choices)}
        for option in choices[:8]:
            validation, trial = check(search, option['plans'], retimings)
            validation = simplify_validation(validation)
            if not reviewable(validation):
                result.setdefault('rejectedTrials', []).append(validation)
                continue
            ids = {l['id'] for l in trial['legs']} - set(search.legs)
            result['selected'] = {**option, 'validation': validation, 'demand': details(search, trial, ids)}
            break
        results.append(result)
    return results


def overnight_groups(search, report):
    """Optional joint screens with explicit, unapproved reception windows."""
    options = {c['originatorRoute']: c['selected'] for c in report['candidates']}
    early_windows = [
        {'id': 'JAX-T1', 'hub': 'JAX', 'startMinute': 90, 'endMinute': 150},
        {'id': 'JAX-T2', 'hub': 'JAX', 'startMinute': 160, 'endMinute': 220},
    ]
    scenarios = [
        ('MCI-BHM overnight group', {346: 293, 303: 320}, early_windows, {'JAX': 17}),
        ('MCI-BHM-PHF-DAY overnight group', {346: 293, 303: 320, 518: 270, 139: 306},
         early_windows + [
             {'id': 'JAX-T3', 'hub': 'JAX', 'startMinute': 1380, 'endMinute': 1440},
             {'id': 'DAY-B9', 'hub': 'DAY', 'startMinute': 1260, 'endMinute': 1320},
         ], {'JAX': 18, 'DAY': 9}),
    ]
    results = []
    for name, morning_clocks, banks, counts in scenarios:
        if not all(route in options for route in morning_clocks):
            continue
        bank_overlay = {'id': 'unapproved-overnight-reception-windows',
                        'baseSchedule': {'scheduleId': search.base['schedule']['id']},
                        'schedule': {'id': 'v122-overnight-group-analysis', 'label': name, 'status': 'draft'},
                        'hubBanksToAdd': banks, 'hubBankCountOverrides': counts}
        trial_base = apply_optimization_overlay(search.base, bank_overlay)
        trial_search = HoldSearch(trial_base)
        plans = []
        ground = []
        for route, dep in morning_clocks.items():
            chosen = deepcopy(options[route]['plans'])
            city = chosen[1]['legs'][0]['destination']
            first = next(l for l in search.base['legs'] if l['route'] == route and l['sequenceWithinRoute'] == 1)
            chosen[1]['legs'][0] = search.leg('JAX', city, dep, first['fleet'])
            ground.append({'route': route, 'city': city, 'originalOriginator': first['departure'],
                           'morningGroundMinutes': first['departureMinute'] - chosen[1]['legs'][0]['arrivalMinute']})
            plans.extend(chosen)
        validation, trial = check(trial_search, plans)
        ids = {l['id'] for l in trial['legs']} - set(search.legs)
        result = {'name': name, 'status': 'hypothetical joint group; not approved or applied',
                  'banksToAdd': banks, 'hubBankCountChanges': counts, 'plans': plans,
                  'originatorBuffers': ground, 'validation': simplify_validation(validation),
                  'demand': details(trial_search, trial, ids)}
        results.append(result)
    return results


def recommendations():
    return {'nextBestOvernightGroups': [[302, 303], [345, 346]],
            'secondaryOvernightGroups': [[517, 518], [138, 139]],
            'compatibleWithExistingEveningBankButLowerDemand': [[307, 308], [308, 309]],
            'alternativeAircraftForMci': [[116, 117]],
            'alternativeAircraftForPhf': [[314, 315], [328, 329]],
            'lowPriority': [[331, 332], [163, 164], [304, 305]],
            'notes': ['Select one MCI and one PHF alternative, or retime and validate the combination: their selected morning departures are less than 30 minutes apart.',
                      'MCI/BHM arrivals after midnight connect into the following morning. These do not feed the 20:45–21:45 evening bank.',
                      'MCI has only 127 minutes at JAX in the buffered joint plan; crew coverage and maintenance availability need separate review.',
                      'RDU morning return timing fits, but its existing 06:30 JAX departure makes the additional early departure fail pairing-spacing rules.',
                      'SHV cannot lose its sole destination terminator without resolving destination RON coverage.'],
            'approvalStatus': 'Review only; user has approved the first draft, not these additional opportunities.'}


def main():
    base = read_json(ROOT / BASE)
    search = HoldSearch(base)
    routes, lines = defaultdict(list), defaultdict(list)
    for leg in base['legs']:
        routes[leg['route']].append(leg)
    for sequence in routes.values():
        sequence.sort(key=lambda l: l['sequenceWithinRoute'])
        lines[sequence[0]['line']].append(sequence)
    preceding = {}
    for sequences in lines.values():
        sequences.sort(key=lambda s: s[0]['day'])
        for previous, current in zip(sequences, sequences[1:] + sequences[:1]):
            preceding[current[0]['route']] = previous
    inventory, candidates = [], []
    for route, sequence in sorted(routes.items()):
        first = sequence[0]
        prior = preceding[route]
        last = prior[-1]
        city, fleet = first['origin'], first['fleet']
        assert last['destination'] == city
        finish = route_finish(search, prior)
        item = {'originatorRoute': route, 'previousRoute': last['route'],
                'line': first['line'], 'day': first['day'], 'fleet': fleet, 'city': city,
                'firstFlight': first['flight'], 'originalOriginator': first['departure'],
                'previousTermination': clock(finish), 'previousTerminationMinute': finish,
                'group': search.screen.cities[city]['group']}
        if city == 'JAX':
            item['status'] = 'already-based-at-JAX'
            inventory.append(item)
            continue
        inbound_shift = search.leg(city, 'JAX', 0, fleet)['arrivalMinute']
        outbound_shift = search.leg('JAX', city, 0, fleet)['arrivalMinute']
        latest_morning = first['departureMinute'] - 40 - outbound_shift
        earliest_night = finish + 40
        last_night = 1410 if city in search.screen.hubs else 1260
        item.update(blockMinutes=search.screen.utc(search.leg('JAX', city, 270, fleet))[2],
                    earliestMorningArrival=clock(270 + outbound_shift),
                    latestMorningJaxDeparture=clock(latest_morning),
                    earliestEveningDeparture=clock(earliest_night),
                    earliestEveningJaxArrival=clock(earliest_night + inbound_shift),
                    morningShortfallMinutes=max(0, 270 - latest_morning),
                    eveningDepartureShortfallMinutes=max(0, earliest_night - last_night),
                    currentFrequencyToJax=len(search.pairs[city, 'JAX']),
                    currentFrequencyFromJax=len(search.pairs['JAX', city]),
                    localOdBothDirections=search.screen.od[city]['JAX'] + search.screen.od['JAX'][city])
        reasons = []
        if latest_morning < 270:
            reasons.append('cannot-return-before-originator')
        if earliest_night > last_night:
            reasons.append('previous-finish-too-late-for-normal-departure')
        if reasons:
            item['status'] = 'blocked-by-timing'
            item['reasons'] = reasons
            inventory.append(item)
            continue
        choices = []
        for dep in points(search, city, fleet, earliest_night, last_night, True):
            inbound = search.leg(city, 'JAX', dep, fleet)
            for back in points(search, city, fleet, 270, latest_morning, False):
                outbound = search.leg('JAX', city, back, fleet)
                if back + 1440 - inbound['arrivalMinute'] < 40:
                    continue
                if not search.spacing([inbound, outbound]):
                    continue
                plans = [{'route': last['route'], 'legs': [inbound]}, {'route': route, 'legs': [outbound]}]
                needs = bank_requirements(search, plans)
                score, values = search.score([inbound, outbound])
                choices.append({'plans': plans, 'bankRequirements': needs, 'score': score, 'legScores': values,
                                'morningGroundMinutes': first['departureMinute'] - outbound['arrivalMinute'],
                                'jaxOvernightMinutes': back + 1440 - inbound['arrivalMinute']})
        item['timingChoices'] = len(choices)
        if not choices:
            item['reasons'] = ['no-pairing-spacing-compatible-overnight-pair']
        # Prefer satisfying more of the existing bank structure, then demand.
        # Separately retain the best score to expose the cost of bank restrictions.
        ranked = sorted(choices, key=lambda c: (len(c['bankRequirements']), -c['score'], -c['morningGroundMinutes']))
        alternatives = sorted(choices, key=lambda c: -c['score'])[:4]
        tested = set()
        selected = []
        for option in ranked[:12] + alternatives:
            identity = tuple(l['departureMinute'] for p in option['plans'] for l in p['legs'])
            if identity in tested:
                continue
            tested.add(identity)
            validation, trial = check(search, option['plans'])
            validation = simplify_validation(validation)
            physically_valid = reviewable(validation)
            if not physically_valid:
                item.setdefault('rejectedTrials', []).append({'times': identity, 'validation': validation})
                continue
            ids = {l['id'] for l in trial['legs']} - set(search.legs)
            selected.append({**option, 'validation': validation, 'demand': details(search, trial, ids)})
            # Best bank-compatible option, and optionally a higher-demand off-bank sensitivity.
            if not selected[0]['bankRequirements'] or len(selected) == 2:
                break
        if not selected:
            item['status'] = 'no-validated-option'
        else:
            item['status'] = ('conditional-bank-and-hub-count-change'
                              if any(c['check'] == 'tiered_service_minimums' for c in selected[0]['validation']['blocking'])
                              else 'fully-feasible' if not selected[0]['bankRequirements'] else 'conditional-bank-change')
            candidates.append({**item, 'selected': selected[0], 'alternative': selected[1] if len(selected) > 1 else None})
            print(route, city, item['status'],
                  [(l['departureClock'], l['arrivalClock'], round(l['local'], 1), round(l['connecting'], 1))
                   for l in selected[0]['demand']], 'bankNeeds', selected[0]['bankRequirements'], flush=True)
        inventory.append(item)
    report = {'workVersion': '1.2.2', 'status': 'analysis-only; no additional flights approved by this screen',
              'baseCanonical': BASE, 'baseSha256': sha256_file(ROOT / BASE), 'demandId': search.screen.demand_id,
              'scope': 'Every cyclic aircraft-day boundary, all 181 routes and 20 lines. Main screen adds spoke/hub→JAX to the predecessor and JAX→original-originator-city to the successor, preserving all existing flight clocks and identities. Separate optional predecessor-retiming sensitivities explicitly list changes. Include each line last-to-first boundary.',
              'interpretation': 'Full-capture seat-uncapped relative-choice opportunity units, not passenger forecasts or net incremental demand.',
              'summary': {'routesScreened': len(inventory), 'alreadyBasedAtJax': sum(i['status'] == 'already-based-at-JAX' for i in inventory),
                          'morningTimingFits': sum(i.get('morningShortfallMinutes') == 0 for i in inventory),
                          'fullyFeasible': sum(i['status'] == 'fully-feasible' for i in inventory),
                          'conditionalBankChanges': sum(i['status'] == 'conditional-bank-change' for i in inventory),
                          'conditionalBankAndHubCountChanges': sum(i['status'] == 'conditional-bank-and-hub-count-change' for i in inventory)},
              'inventory': inventory, 'candidates': candidates,
              'notes': ['Off-bank operations remain validation errors and require an explicit later scheduling decision; no analysis-only approved overrides are applied.',
                        'A previous late finish can block this addition even when the morning return fits comfortably.',
                        'Existing JAX-originating Routes, including the accepted 514→515 PIE group, are not duplicated.',
                        'These are individual candidate screens. Any selected combination must be validated together for spacing, gates, stands and shared aircraft-day boundaries.']}
    report['optionalPredecessorRetimings'] = close_misses(search, report)
    report['optionalJointOvernightGroups'] = overnight_groups(search, report)
    report['recommendations'] = recommendations()
    write_json(ROOT / REPORT, report)
    print(report['summary'], flush=True)


if __name__ == '__main__':
    main()
