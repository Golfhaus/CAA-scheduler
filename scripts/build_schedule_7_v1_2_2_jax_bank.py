"""Build the user-approved, unpublished first v1.2.2 JAX-bank draft."""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_2_jax_bank import BANK, details
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.timetable import export_timetable

BASE = 'data/schedules/schedule_7_v1_2_1/canonical_schedule.json'
OVERLAY = 'config/optimizations/schedule_7_v1_2_2_round_1.json'
CANONICAL = 'data/schedules/schedule_7_v1_2_2_draft/canonical_schedule.json'
REPORT = 'config/proposals/schedule_7_v1_2_2_draft.json'
FLYING = [
    (702, 'SFB', 'JAX', 1205), (702, 'JAX', 'SFB', 1293),
    (704, 'SFB', 'BHM', 1219), (704, 'BHM', 'SFB', 1395),
    (341, 'MSY', 'JAX', 1104), (341, 'JAX', 'MSY', 1299),
    (504, 'CLT', 'JAX', 1174), (504, 'JAX', 'CLT', 1285),
    (338, 'SAV', 'JAX', 1200), (338, 'JAX', 'SAV', 1285),
    (514, 'PIE', 'JAX', 1214), (515, 'JAX', 'PIE', 380),
]


def make_overlay(base):
    search = HoldSearch(base)
    fleets = {l['route']: l['fleet'] for l in base['legs']}
    additions, assignments = [], []
    for route, origin, destination, dep in FLYING:
        index = 1 + sum(l['route'] == route for l in additions)
        leg = {**search.leg(origin, destination, dep, fleets[route]),
               'id': f'V122-R{route}-{index}-{origin}-{destination}', 'route': route}
        additions.append(leg)
        for operation, city, minute in [('departure', origin, leg['departureMinute']),
                                         ('arrival', destination, leg['arrivalMinute'])]:
            if city not in base['operatingPolicy']['hubs']:
                continue
            bank = BANK['id'] if city == 'JAX' and BANK['startMinute'] <= minute < BANK['endMinute'] else search.bank(city, minute)
            if not bank:
                raise ValueError(f'No bank for {leg["id"]} {operation}')
            assignments.append({'legId': leg['id'], 'operation': operation, 'bankId': bank})
    first_two = sorted((l for l in base['legs'] if l['route'] == 515), key=lambda l: l['sequenceWithinRoute'])[:2]
    retimings = [{'legId': l['id'], 'expectedDepartureMinute': l['departureMinute'],
                  'expectedArrivalMinute': l['arrivalMinute'], 'departureMinute': l['departureMinute'] + 9,
                  'arrivalMinute': l['arrivalMinute'] + 9,
                  'reason': 'Provide 50 minutes at PIE after the JAX morning return while preserving the SYR bank.'} for l in first_two]
    return {'schemaVersion': '1.0.0', 'id': 'schedule-7-v1.2.2-jax-bank-round-1',
            'baseSchedule': {'scheduleId': base['schedule']['id'], 'canonical': BASE, 'sha256': sha256_file(ROOT / BASE)},
            'schedule': {'id': 'schedule_7_v1_2_2_draft', 'version': '1.2.2',
                         'label': 'Schedule 7 v1.2.2 unpublished draft', 'status': 'draft'},
            'approval': {'status': 'approved-for-draft', 'date': '2026-10-03', 'instruction': 'Add as you suggest.',
                         'scope': 'Prior SFB extensions, JAX 20:45–21:45 bank, Routes 341/504/338 evening turns, Route 514/515 PIE overnight group and nine-minute Route 515 retiming.',
                         'publication': 'Reserved to user decision'},
            'hubBanksToAdd': [BANK], 'hubBankCountOverrides': {'JAX': 15},
            'insertLegs': additions, 'retimeLegs': retimings,
            'bankAssignmentsToAdd': assignments, 'operatingOverrides': []}


def build():
    base = read_json(ROOT / BASE)
    change = make_overlay(base)
    candidate = apply_optimization_overlay(base, change)
    old = {l['id']: l for l in base['legs']}
    retimed = {r['legId'] for r in change['retimeLegs']}
    for leg in candidate['legs']:
        if leg['id'] in old:
            keys = ('flight', 'route', 'line', 'day', 'fleet', 'origin', 'destination', 'pairing')
            if leg['id'] not in retimed:
                keys += ('departureMinute', 'arrivalMinute')
            assert all(leg[k] == old[leg['id']][k] for k in keys)
    structural = validate_schedule(candidate)
    operating = validate_operating_rules(candidate)
    overnight = validate_overnight_turns(candidate)
    planning = reconstruct_planning_snapshot(candidate)
    planning_check = validate_planning_snapshot(planning, candidate)
    assert structural['status'] == planning_check['status'] == overnight['status'] == 'pass'
    assert not operating['summary']['effectiveErrorFindings']
    assert not any(c['hardStop'] and c['status'] == 'fail' for c in operating['checks'])
    gates = export_gate_schedule(candidate)
    stands = [c for city in gates['cities'] for c in city['claims'] if c['rowType'] == 'stand']
    search = HoldSearch(base)
    new_ids = {l['id'] for l in candidate['legs']} - set(old)
    demand = details(search, candidate, new_ids)
    report = {'workVersion': '1.2.2', 'status': 'draft; unpublished', 'baseCanonical': BASE,
              'overlay': OVERLAY, 'canonical': CANONICAL, 'approval': change['approval'],
              'demandId': search.screen.demand_id,
              'demandInterpretation': 'Full-capture seat-uncapped relative-choice opportunities, not passenger forecasts or net incremental demand.',
              'summary': {'legs': len(candidate['legs']), 'addedLegs': len(new_ids),
                          'routes': len({l['route'] for l in candidate['legs']}),
                          'lines': len({l['line'] for l in candidate['legs']}),
                          'effectiveOperatingErrors': operating['summary']['effectiveErrorFindings'],
                          'effectiveOperatingWarnings': operating['summary']['effectiveWarningFindings'],
                          'hardStopFailures': 0, 'structural': structural['status'], 'planning': planning_check['status'],
                          'overnight': overnight['status'], 'gates': 'pass',
                          'standClaims': len(stands), 'standMinutes': sum(c['end']-c['start'] for c in stands)},
              'bankAdded': BANK, 'newFlights': demand,
              'retimings': [{**r, 'flight': old[r['legId']]['flight']} for r in change['retimeLegs']],
              'pendingDecisions': ['Any further late-originator opportunities', 'Publication'],
              'originalReleaseManifestUnchanged': True}
    write_json(ROOT / OVERLAY, change)
    write_json(ROOT / CANONICAL, candidate)
    write_json(ROOT / REPORT, report)
    output = ROOT / 'builds/schedule_7_v1_2_2_draft'
    for filename, value in {'canonical_schedule.json': candidate, 'validation_report.json': structural,
                           'operating_validation_report.json': operating, 'overnight_turn_validation.json': overnight,
                           'planning_snapshot.json': planning, 'planning_validation_report.json': planning_check,
                           'gates.json': gates, 'timetable.json': export_timetable(candidate)}.items():
        write_json(output / filename, value)
    return report


if __name__ == '__main__':
    result = build()
    print(result['summary'])
    for leg in result['newFlights']:
        print(leg['route'], leg['flight'], leg['origin'], leg['departureClock'], leg['destination'], leg['arrivalClock'])
