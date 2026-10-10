"""Accept the reviewed PHF/MCI exchange into the unpublished v1.2.4 draft."""
from copy import deepcopy
from pathlib import Path
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import validate, demand
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4 import cache_network
from analyze_schedule_7_v1_2_4_midnight_retimings import operating_evidence

BASE = 'data/schedules/schedule_7_v1_2_4_round_4/canonical_schedule.json'
DRAFT = 'data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json'
RELEASE = 'data/schedules/schedule_7_v1_2_3/canonical_schedule.json'
REPORT = 'data/schedules/schedule_7_v1_2_4_draft/draft_report.json'
INCREMENTAL = 'config/optimizations/schedule_7_v1_2_4_accepted_round_5.json'
CUMULATIVE = 'config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_5.json'
REVIEW = 'config/proposals/schedule_7_v1_2_4_midnight_retimings_review.json'
PROPOSAL = 'config/proposals/schedule_7_v1_2_4_mid_retime_337_345_preserve.json'


def same(a, b, path='model'):
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-8), (path, a, b)
    elif isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            same(a[k], b[k], path + '.' + str(k))
    elif isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, path + '.' + str(i))
    else:
        assert a == b, (path, a, b)


def main():
    base = read_json(ROOT / BASE)
    released = read_json(ROOT / RELEASE)
    review = read_json(ROOT / REVIEW)
    assert review['baseSha256'] == sha256_file(ROOT / BASE)
    q = next(x for x in review['candidates'] if x['id'] == 'MID-RETIME-337-345-PRESERVE')
    c = deepcopy(read_json(ROOT / PROPOSAL))
    assert c['baseSchedule']['sha256'] == sha256_file(ROOT / BASE)
    c['id'] = 'schedule-7-v1.2.4-accepted-round-5'
    c['schedule'].update(id='schedule_7_v1_2_4_draft', label='Schedule 7 v1.2.4 working draft; unpublished')
    c['approval'] = {
        'status': 'approved for draft implementation; unpublished',
        'userInstruction': 'Add the current recommendations to the draft.',
        'scope': 'Source routes 337/345 PHF–MCI reciprocal exchange arriving by 00:01 local; '
                 'Flights 1404/1319/1320/1784/1589 advanced 12/16/16/3/1 minutes; '
                 'two MCI banks shifted one minute earlier; PHF midnight arrival bank; '
                 'AH/AK/AL/AS rebuilt into 9/9/12/11-day cycles. SYR and other alternatives deferred.',
        'publication': 'Reserved to user decision',
    }
    s = HoldSearch(base)
    cache_network(s)
    v, trial = validate(s, c)
    assert good(v), v
    current = read_json(ROOT / DRAFT)
    assert current == base or current == trial, 'Draft diverged from the reviewed input'
    mapping = {x['sourceRoute']: x for x in c['routeReassignments']}
    old = {x['id']: x for x in base['legs']}
    now = {x['id']: x for x in trial['legs']}
    changes = {x['legId']: x for x in c['retimeLegs']}
    for identifier, leg in old.items():
        expected = deepcopy(leg)
        if leg['route'] in mapping:
            m = mapping[leg['route']]
            expected.update(route=m['targetRoute'], line=m['line'], day=m['day'])
        if identifier in changes:
            change = changes[identifier]
            expected.update(departureMinute=change['departureMinute'], arrivalMinute=change['arrivalMinute'],
                            departure=now[identifier]['departure'], arrival=now[identifier]['arrival'])
        expected['sequenceWithinRoute'] = now[identifier]['sequenceWithinRoute']
        assert expected == now[identifier], identifier
    assert len(trial['legs']) == 1170
    inserted = {x['id'] for x in c['insertLegs']}
    assert {now[x]['flight'] for x in inserted} == {2171, 2172}
    assert all(now[x]['arrivalMinute'] <= 1441 for x in inserted)
    assert trial['schedule']['fleetCounts'] == base['schedule']['fleetCounts']

    prior = deepcopy(read_json(ROOT / 'config/optimizations/schedule_7_v1_2_4_accepted_rounds_1_4.json'))
    assert prior['baseSchedule']['sha256'] == sha256_file(ROOT / RELEASE)
    # Route reassignment occurs before insertion in the overlay engine. Earlier
    # accepted insertions must therefore use their final route identities.
    for addition in prior['insertLegs']:
        if addition['route'] in mapping:
            addition['route'] = mapping[addition['route']]['targetRoute']
    for key in ('insertLegs', 'retimeLegs', 'bankAssignmentsToAdd', 'bankAssignmentReplacements',
                'hubBanksToAdd', 'operatingOverrides', 'routeReassignments', 'hubBankChanges'):
        prior.setdefault(key, []).extend(deepcopy(c.get(key, [])))
    prior.setdefault('hubBankCountOverrides', {}).update(c['hubBankCountOverrides'])
    prior['id'] = 'schedule-7-v1.2.4-accepted-rounds-1-5'
    scope = prior['approval']['scope']
    prior['approval'] = deepcopy(c['approval'])
    prior['approval']['scope'] = scope + ' ' + c['approval']['scope']
    prior['schedule'] = deepcopy(c['schedule'])
    assert apply_optimization_overlay(released, prior) == trial, 'Cumulative replay differs'
    print('1170-flight draft and exact cumulative replay validated', flush=True)

    actual_demand = demand(s, trial, inserted)
    incremental_audit = audit(s, trial)
    same(actual_demand, q['demand'])
    same(incremental_audit, q['connectionAudit'])
    evidence = operating_evidence(base, trial, q['lineProof']['poolLines'])
    assert evidence['section26']['checkA'] == 'pass'
    assert evidence['section26']['newCheckBFindings'] == 0
    assert evidence['section26']['worsenedCheckBGaps'] == 0
    rs = HoldSearch(released, allocate_gates=False)
    cumulative_audit = audit(rs, trial)
    print('Reviewed demand and connection tradeoffs reproduced', flush=True)

    historic = ROOT / 'data/schedules/schedule_7_v1_2_4_round_4/draft_report.json'
    old_report = read_json(ROOT / REPORT) if current == base else read_json(historic)
    assert old_report['canonicalSha256'] == sha256_file(ROOT / BASE)
    if not historic.exists():
        write_json(historic, old_report)
    write_json(ROOT / INCREMENTAL, c)
    write_json(ROOT / CUMULATIVE, prior)
    write_json(ROOT / DRAFT, trial)
    report = deepcopy(old_report)
    report.update(acceptedOverlay=CUMULATIVE, acceptedOverlaySha256=sha256_file(ROOT / CUMULATIVE),
                  canonicalSha256=sha256_file(ROOT / DRAFT), validation=v,
                  connectionTradeoff=cumulative_audit, round5IncrementalTradeoff=incremental_audit,
                  round5Demand=actual_demand, round5OperatingEvidence=evidence,
                  round5SourceRoutes=[337, 345], round5RouteReassignments=c['routeReassignments'],
                  round5LineProof=q['lineProof'], round5AcceptedOverlay=INCREMENTAL)
    report['acceptedRoutes'] = [mapping[x]['targetRoute'] if x in mapping else x for x in old_report['acceptedRoutes']]
    report['acceptedRoutes'].extend(x['route'] for x in c['insertLegs'])
    report['acceptedRouteLabels'] = 'Current route numbers after round-five reconstruction; historic per-round reports retain source numbers.'
    report['summary'].update(flights=1170, addedFlights=18,
                             retimedReleasedFlights=[1404, 1319, 1320, 1784, 1589, 1739, 1811],
                             unchangedReleasedFlightClocks=1145)
    report['checks']['round5ReviewedDemandAndAuditReproduction'] = 'pass'
    report['checks']['approvedRouteReconstructionAndFlightIdentityPreservation'] = 'pass'
    # The old list pertains to round four; do not present it as a refreshed list.
    report['round4NewWarningFindings'] = report.pop('newWarningFindings', [])
    write_json(ROOT / REPORT, report)
    print('ACCEPTED: flights 2171/2172 in draft; main and live app unchanged', flush=True)


if __name__ == '__main__':
    main()
