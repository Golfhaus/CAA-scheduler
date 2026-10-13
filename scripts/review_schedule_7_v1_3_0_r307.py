"""Review, never accept, PIT-BHM-PIT inside Route 307's current hold."""
from pathlib import Path
import copy, csv, hashlib, json, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from caa_scheduler.bank_placement import _block_minutes, TIMEZONE_OFFSETS
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.validation import validate_schedule
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.planning import haversine_nm, reconstruct_planning_snapshot, validate_planning_snapshot
from caa_scheduler.gate_export import export_gate_schedule

BASE = ROOT / 'data/schedules/schedule_7_v1_3_0_draft/canonical_schedule.json'
raw = BASE.read_bytes()
prior_review = ROOT / 'outputs/schedule_7_v1_3_0_r307/review.json'
if prior_review.exists() and json.loads(prior_review.read_text())['baseSha256'] != hashlib.sha256(raw).hexdigest():
    raise ValueError('Historical BHM review baseline changed. Reproduce at commit c3f51b03aa326cc5933c0754be764030566cac21; use the release builder for current flying.')
base = json.loads(raw)
by_flight = {l['flight']: l for l in base['legs']}
cities = {c['code']: c for c in base['cities']}
profile = next(p for p in json.loads((ROOT / 'config/policies/planning_rules_v7.json').read_text())['frequencyAllocation']['fleetProfiles'] if p['fleet'] == 'CRJ700')
block = _block_minutes('PIT', 'BHM', profile, cities)
turn = base['operatingPolicy']['turns']['minimumMinutes']
hold = by_flight[1918]['departureMinute'] - by_flight[1917]['arrivalMinute']
required = 2 * block + 3 * turn
shortfall = required - hold
assert block == 106 and hold == 322 and shortfall == 10
directory = ROOT / 'outputs/schedule_7_v1_3_0_r307'
directory.mkdir(parents=True, exist_ok=True)

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def leg(a, b, departure, identifier):
    arrival = departure + block + TIMEZONE_OFFSETS[cities[b]['timezone']] - TIMEZONE_OFFSETS[cities[a]['timezone']]
    return {'id': identifier, 'route': 307, 'origin': a, 'destination': b, 'departureMinute': departure, 'arrivalMinute': arrival}

def shift(flight, minutes):
    l = by_flight[flight]
    return {'legId': l['id'], 'expectedDepartureMinute': l['departureMinute'], 'expectedArrivalMinute': l['arrivalMinute'], 'departureMinute': l['departureMinute'] + minutes, 'arrivalMinute': l['arrivalMinute'] + minutes}

rows = list(csv.reader((ROOT / 'data/reference/airport_od_matrix_consolidated_v2.csv').read_text().splitlines()))
header = next(i for i, r in enumerate(rows) if r and r[0] == 'Origin \\ Dest')
codes = rows[header][1:]
od = {r[0]: dict(zip(codes, (float(v) if v.strip() else None for v in r[1:]))) for r in rows[header+1:] if r and r[0] in cities}
distance = haversine_nm(cities['PIT']['latitude'], cities['PIT']['longitude'], cities['BHM']['latitude'], cities['BHM']['longitude'])
report = {'baseSha256': hashlib.sha256(raw).hexdigest(), 'status': 'review only; not accepted', 'route': 307, 'fleet': 'CRJ700', 'currentHold': {'arrival': '11:24 ET', 'departure': '16:46 ET', 'minutes': hold}, 'blockModel': {'distanceNm': distance, 'profile': profile, 'blockMinutesEachWay': block}, 'minimumTurns': turn, 'requiredMinutes': required, 'shortfallMinutes': shortfall, 'fitsUnchanged': shortfall <= 0, 'directOdPerDay': {'PIT-BHM': od['PIT']['BHM'], 'BHM-PIT': od['BHM']['PIT']}, 'trials': {}}

for name, first_turn, bhm_turn, pit_shift, phf_shift in [('minimum',40,40,10,17), ('buffered',45,45,20,25)]:
    out = leg('PIT', 'BHM', by_flight[1917]['arrivalMinute'] + first_turn, 'V130-R307-PIT-BHM')
    incoming = leg('BHM', 'PIT', out['arrivalMinute'] + bhm_turn, 'V130-R307-BHM-PIT')
    overlay = {'schemaVersion':'1.0.0', 'id':'schedule-7-v1.3.0-proposed-r307-'+name, 'baseSchedule':{'scheduleId':base['schedule']['id'],'canonical':BASE.relative_to(ROOT).as_posix(),'sha256':report['baseSha256']}, 'schedule':{'id':'schedule_7_v1_3_0_proposal_r307_'+name,'version':'1.3.0-analysis','label':'Unpublished R307 BHM '+name+' proposal','status':'draft'}, 'approval':{'status':'review only; unchanged hold does not fit, modifications not accepted','publication':'Not authorized'}, 'retimeLegs':[shift(1918,pit_shift),shift(1401,phf_shift)], 'insertLegs':[out,incoming], 'bankAssignmentReplacements':[{'legId':by_flight[1401]['id'],'operation':'departure','bankId':'PHF-M6'}]}
    candidate = apply_optimization_overlay(base, overlay)
    structural = validate_schedule(candidate)
    operating = validate_operating_rules(candidate)
    overnight = validate_overnight_turns(candidate)
    planning = validate_planning_snapshot(reconstruct_planning_snapshot(candidate, demand_data_version='bts-db1c-6mo-jul2025-apr2026-v7'),candidate)
    gates = export_gate_schedule(candidate)
    stands = [s for c in gates['cities'] for s in c['claims'] if s['rowType']=='stand']
    valid = structural['status']=='pass' and operating['summary']['effectiveErrorFindings']==0 and not any(c['hardStop'] and c['status']=='fail' for c in operating['checks']) and overnight['status']=='pass' and planning['status']=='pass'
    altered = {r['legId'] for r in overlay['retimeLegs']}
    for old in base['legs']:
        new = next(l for l in candidate['legs'] if l['id']==old['id'])
        permitted = {'sequenceWithinRoute'} | ({'departure','arrival','departureMinute','arrivalMinute'} if old['id'] in altered else set())
        assert all(old[k]==new[k] for k in old if k not in permitted)
    assert candidate['operatingPolicy']==base['operatingPolicy'] and candidate['hubBanks']==base['hubBanks']
    flights = [l for l in candidate['legs'] if l['route']==307]
    clocks = {l['flight']:l for l in flights}
    new = [l for l in flights if l['id'] in {out['id'],incoming['id']}]
    ground = [first_turn,bhm_turn,clocks[1918]['departureMinute']-incoming['arrivalMinute'],clocks[1401]['departureMinute']-clocks[1918]['arrivalMinute']]
    row = {'valid':valid,'newFlights':new,'existingFlightChanges':[{'flight':f,'before':by_flight[f],'after':clocks[f]} for f in [1918,1401]],'groundMinutesPIT_BHM_PIT_PHF':ground,'structural':structural['summary'],'operating':operating['summary'],'overnightStatus':overnight['status'],'planningStatus':planning['status'],'failedChecks':[c for c in operating['checks'] if c['status']=='fail'],'standClaims':len(stands),'standMinutes':sum(s['end']-s['start'] for s in stands),'stations':[{k:c[k] for k in ['code','nGates','nStands','peakUsed']} for c in gates['cities'] if c['code'] in ['PIT','BHM','PHF']]}
    report['trials'][name] = row
    write(ROOT / f'config/proposals/schedule_7_v1_3_0_r307_{name}.json',overlay)
    write(directory / f'{name}_canonical.json',candidate)
    print(name,valid,ground,operating['summary'])

assert BASE.read_bytes()==raw, 'Review changed accepted draft'
write(directory/'review.json', report)
