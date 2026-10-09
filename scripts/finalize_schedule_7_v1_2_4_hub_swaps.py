"""Add explicit spacing evidence and a complete route-level review. No schedule edits."""
from collections import Counter, defaultdict
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules
from analyze_schedule_7_v1_2_4_hub_swaps import BASE, OUT, clock

def finalize():
    base, review = read_json(ROOT / BASE), read_json(ROOT / OUT)
    assert sha256_file(ROOT / BASE) == review['baseSha256']
    assert (ROOT / BASE).read_bytes() == (ROOT / 'data/schedules/schedule_7_v1_2_4_draft/canonical_schedule.json').read_bytes()
    base_checks = {x['id']: x for x in validate_operating_rules(base)['checks']}
    key_a, key_b = 'section_26_pairing_spacing', 'section_26_city_departure_gap'
    all_candidates = review['pairs'] + review.get('coordinatedCandidates', [])
    validated = [q for q in all_candidates if q.get('overlay')]
    for q in validated:
        overlay = read_json(ROOT / q['overlay'])
        overlay['approval']['scope'] = f"{len(overlay['insertLegs'])} reciprocal extension legs with explicit line rebuilding and additional bank windows. Original clocks retained."
        write_json(ROOT / q['overlay'], overlay)
        trial = apply_optimization_overlay(base, overlay)
        checks = {x['id']: x for x in validate_operating_rules(trial)['checks']}
        assert not checks[key_a]['findings']
        before = {x['id']: x['evidence'] for x in base_checks[key_b]['findings']}
        after = {x['id']: x['evidence'] for x in checks[key_b]['findings']}
        assert set(after).issubset(before)
        for city, finding in after.items():
            assert max(x['minutes'] for x in finding['excessiveGaps']) <= max(x['minutes'] for x in before[city]['excessiveGaps'])
        evidence = []
        for leg in overlay['insertLegs']:
            times = sorted(l['departureMinute'] % 1440 for l in trial['legs'] if (l['origin'], l['destination']) == (leg['origin'], leg['destination']))
            gaps = [(b - a) % 1440 for a, b in zip(times, times[1:] + times[:1])]
            assert min(gaps) >= 30 and len(times) <= 6
            evidence.append({'legId': leg['id'], 'origin': leg['origin'], 'destination': leg['destination'], 'departures': times,
                             'minimumCyclicGapMinutes': min(gaps), 'frequencyBefore': len(times) - 1, 'frequencyAfter': len(times)})
        q['section26Evidence'] = {'checkA': 'pass', 'newCheckBFindings': 0, 'worsenedCheckBGaps': 0,
                                 'baselineCheckBCities': len(before), 'candidateCheckBCities': len(after), 'pairs': evidence}
    for x in review['eligible']:
        qs = [q for q in review['pairs'] if x['route'] in q['routes']]
        single = [q['id'] for q in qs if q.get('overlay')]
        joint = [q['id'] for q in review.get('coordinatedCandidates', []) if x['route'] in q['routes'] and q.get('overlay')]
        timing = sum('selectedTiming' in q for q in qs)
        if joint:
            disposition = 'Conditional coordinated swap. Both pairs must be adopted together.'
        elif single:
            disposition = 'Conditional individual swap. New banks and line rebuilding required.'
        elif timing:
            disposition = 'Timing possible with new banks. No compliant line reconstruction proved in the bounded search.'
        else:
            disposition = 'No reciprocal timing with current flight clocks, curfews, turn minimums and spacing.'
        x['review'] = {'screenedPairs': len(qs), 'timingPairs': timing, 'validatedIndividualOptions': single,
                       'validatedCoordinatedOptions': joint, 'disposition': disposition}
    review['counts']['fullyValidatedCoordinatedPlans'] = sum(bool(q.get('overlay')) for q in review.get('coordinatedCandidates', []))
    review['counts']['terminatorsWithValidatedOption'] = sum(bool(x['review']['validatedIndividualOptions'] or x['review']['validatedCoordinatedOptions']) for x in review['eligible'])
    review['limitations'] = [
        'No reciprocal option fits the existing banks. All validated alternatives are conditional on explicit bank additions and line rebuilding.',
        'Individual alternatives share aircraft days and line pools. They must not be stacked without a new joint validation.',
        'Line search preserves complete aircraft days and original flight clocks. It considers the paired lines plus up to two other same-fleet lines. Failure to prove a cover is not global impossibility.',
        'The coordinated search tests only two disjoint CRJ200 pairs on AD (44 combinations). It is not a fleet-wide multi-pair optimizer.',
        'Demand is seat-uncapped relative-choice opportunity under full capture. It is not predicted passengers, incremental traffic, load factor or profit.',
        'Post-midnight arrival banks do not by themselves create an outbound connection bank. Existing 30–240-minute connections are counted explicitly.',
        'Maintenance cadence and overnight station access pass. Short RONs still require task-duration and crew-duty confirmation before implementation.',
        'Unrelated legacy line-length warnings remain outside the altered pools. Every reconstructed line is 9–12 days. No inherited line-length waiver is applied to a new line.'
    ]
    write_json(ROOT / OUT, review)
    lines = [
        '# Schedule 7 v1.2.4: reciprocal hub terminator review', '',
        'Reviewed the accepted 1,168-flight v1.2.4 draft. No schedule, bank, app or main-branch change is implemented.', '',
        'The requested window contains **29 hub terminators**. Screening matching fleets at different hubs produced **97 reciprocal pairs**. **Zero** fits both directions inside the existing banks. Seventeen individual alternatives and one coordinated four-route plan pass full validation with explicitly proposed new banks and compliant line reconstruction.', '',
        '## Options to pursue', '',
        '**CRJ700 337/344 (PHF/MCI)** has the strongest balanced opportunity among the CRJ700 options and requires only one additional arrival bank. PHF–MCI runs 20:45–22:22 local, followed by MCI–PHF 22:45–02:22 next day on the other aircraft. Opportunity is 90.1 and 130.1 respectively. Its original-route handoffs are 337→345 and 344→338. The latter has only 2h08 on the ground at PHF before 04:30. AA/AH/AL must be reclosed into 10/9/9/9-day lines. Confirm the PHF overnight maintenance task and crew plan before implementing.', '',
        '**CRJ200 159/165 (MCI/SYR)** adds MCI–SYR 22:15–02:00 and SYR–MCI 22:15–00:00, each arrival next day. Opportunity is 101.3 and 33.7. AE/AF reclose into 10/9-day lines. Both hubs require new overnight arrival windows. Handoffs are 159→166 at SYR and 165→160 at MCI.', '',
        '**CRJ200 coordinated 115/136 plus 125/135** is the only proved two-pair AD plan among 44 disjoint combinations. It adds JAX–DAY 21:59–23:58, DAY–JAX 21:05–23:04, DAY–MCI 20:23–21:08, and MCI–DAY 22:45–01:30 next day. Opportunity is 13.1/97.2 and 131.1/37.8. The JAX–DAY direction is weak, so this is primarily a connectivity and rotation-rebuilding proposal. Neither pair works alone under the strict line rule. Together they reclose AD into 9/11/10/10-day lines, retaining the same 40 aircraft-days. New windows are JAX 21:45–22:45 and 23:00–24:00, DAY 23:00–24:00 and 01:00–02:00. Forced handoffs: 115→137, 136→116, 125→136, 135→126.', '',
        '**MAX9:** 703/712 or 703/715 (DAY/MCI) each requires only a new DAY 01:00–02:00 arrival window and rebuilds A/B to 11/12 days. Opportunity is 129.6 outward and 42.2 returning. 712/722 (MCI/PHF) also needs one arrival window, at PHF 02:00–03:00, with opportunity 131.6/52.7. These are more promising than DAY/PHF, whose return opportunity is only about 11–14. The imbalance makes the MAX9 choices secondary to smaller-aircraft proposals.', '',
        '**CRJ900:** reciprocal evening timing exists, but no 9–12-day line cover was proved for 507 or 514 in the bounded pool search. Retain current flying unless a broader rebuild is undertaken.', '',
        '## Complete terminator inventory', '',
        '| Route | Fleet | Line/day | Hub | Arrival | Current next route | Conditional validated options or outcome |',
        '|---:|---|---|---|---|---:|---|'
    ]
    for x in review['eligible']:
        z = x['review']; options = z['validatedIndividualOptions'] + z['validatedCoordinatedOptions']
        result = ', '.join(options) if options else ('No line cover proved' if z['timingPairs'] else 'No reciprocal timing')
        lines.append(f"| {x['route']} | {x['fleet']} | {x['line']}/{x['day']} | {x['terminator']} | {x['arrival']} | {x['nextOriginator']['route']} | {result} |")
    lines += ['', '## Validated individual alternatives', '',
        'All times are local (MCI Central, other hubs Eastern). +1 means arrival on the next calendar day. Opportunity is listed in the same direction order as the flights. These are overlapping alternatives, not a cumulative plan.', '',
        '| Routes | Added flights | Opportunity | Rebuilt line lengths | Additional bank windows |',
        '|---|---|---:|---|---|']
    for q in review['pairs']:
        if not q.get('overlay'): continue
        flights = '; '.join(f"{f['origin']}–{f['destination']} {f['departureClock']}–{f['arrivalClock']}" for f in q['demand']['flights'])
        opp = ' / '.join(f"{f['total']:.1f}" for f in q['demand']['flights'])
        banks = '; '.join(f"{b['hub']} {clock(b['startMinute'])}–{'24:00' if b['endMinute'] == 1440 else clock(b['endMinute'])}" for b in q['proposedBanks'])
        lines.append(f"| {q['id']} | {flights} | {opp} | {'/'.join(map(str,q['lineProof']['cycleLengths']))} | {banks} |")
    lines += ['', '## Rules and validation', '',
        'All 18 validated scenarios retain every existing flight number, clock, fleet and market, and preserve fleet aircraft-day counts. Structural, operating, gate/stand, overnight continuity and planning checks pass with zero blocking findings. Every altered line is 9–12 days and meets its hub/focus overnight and maintenance-cadence requirements. Other pre-existing legacy line warnings are not treated as permission to create a noncompliant line.', '',
        '§2.6 Check A passes across the complete schedule in every validated scenario. Each added directional pairing clears the absolute 30-minute floor, including the overnight cyclic gap, and remains within six departures daily. All these flights are hub-bound, so the even-spacing target does not apply. Check B creates zero new city-gap findings and worsens no existing gap. Gates and stands are checked on the full daily schedule including overnight handoffs.', '',
        'The complete one- and two-stop audit finds no lost market or slower best itinerary in any validated scenario. The workbook separates local and connecting opportunity, counts actual feeder/onward flights, shows geographic groups on both sides, and lists the original and proposed line/day/route assignments.', '',
        '## Scope and limitations', '']
    lines += [f'- {x}' for x in review['limitations']]
    lines += ['', 'Sources: pinned schedule/city/O-D/operating-policy inputs and CAA Build Instructions v2.0 §§1.6a, 2.5, 2.6 and 2.8.',
              f"Input snapshot SHA-256: `{review['baseSha256']}`.", '']
    (ROOT / 'outputs/schedule_7_v1_2_4_hub_swaps/Hub_Terminator_Review.md').write_text('\n'.join(lines))
    print('FINALIZED', review['counts'])

if __name__ == '__main__': finalize()
