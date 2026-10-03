"""Read-only v1.2.2 screen of Routes 702/704 evening SFB hub turns.

Only ignored analysis output is written. Trial overlays, including hypothetical
JAX bank exceptions, stay in memory and are never published or approved here.
"""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from caa_scheduler.io import read_json, write_json
from caa_scheduler.optimization_overlay import apply_optimization_overlay
from caa_scheduler.operating_validation import validate_operating_rules, validate_overnight_turns
from caa_scheduler.validation import validate_schedule
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.gates import GateCapacityError
from caa_scheduler.planning import reconstruct_planning_snapshot, validate_planning_snapshot


def clock(minute):
    minute = int(minute)
    return f"{minute % 1440 // 60:02}:{minute % 60:02}" + (" +1" if minute >= 1440 else "")


def overlay(search, plans, hypothetical_bank_exceptions=False):
    additions, assignments, overrides = [], [], []
    for plan in plans:
        for index, leg in enumerate(plan["legs"], 1):
            item = {**leg, "route": plan["route"],
                    "id": f"V122-ANALYSIS-R{plan['route']}-{index}-{leg['origin']}-{leg['destination']}"}
            additions.append(item)
            for operation, city, minute in [("departure", leg["origin"], leg["departureMinute"]),
                                           ("arrival", leg["destination"], leg["arrivalMinute"])]:
                if city not in search.base["operatingPolicy"]["hubs"]:
                    continue
                bank_id = search.bank(city, minute)
                if not bank_id:
                    # Expose current bank alignment failures; do not invent a bank.
                    bank_id = max((b for b in search.base["hubBanks"] if b["hub"] == city),
                                  key=lambda b: b["endMinute"])["id"]
                    if hypothetical_bank_exceptions:
                        overrides.append({"checkId": "hub_bank_alignment",
                            "findingId": f"{item['id']}-{operation}",
                            "reason": "Hypothetical v1.2.2 evening-turn timing exception for analysis only; not approved.",
                            "approvedBy": "analysis-only (not user approved)", "expiresAfterSchedule": 7})
                assignments.append({"legId": item["id"], "operation": operation, "bankId": bank_id})
    return {"schemaVersion": "1.0.0", "id": "v1.2.2-sfb-evening-analysis",
            "baseSchedule": {"scheduleId": search.base["schedule"]["id"]},
            "schedule": {"id": "schedule_7_v1_2_2_evening_analysis", "version": "1.2.2-analysis",
                         "label": "Unpublished v1.2.2 SFB evening-turn analysis", "status": "draft"},
            "insertLegs": additions, "bankAssignmentsToAdd": assignments,
            "operatingOverrides": overrides}


def validate(search, plans, hypothetical=False):
    trial = apply_optimization_overlay(search.base, overlay(search, plans, hypothetical))
    old = {leg["id"]: leg for leg in search.base["legs"]}
    assert all(leg == old[leg["id"]] for leg in trial["legs"] if leg["id"] in old)
    operating = validate_operating_rules(trial)
    overnight = validate_overnight_turns(trial)
    summary = {"structural": validate_schedule(trial)["status"],
               "planning": validate_planning_snapshot(reconstruct_planning_snapshot(trial), trial)["status"],
               "operatingErrors": operating["summary"]["effectiveErrorFindings"],
               "hardStopFailures": [c["id"] for c in operating["checks"] if c["hardStop"] and c["status"] == "fail"],
               "overnight": overnight["status"], "overnightFindings": overnight["findings"],
               "blockingChecks": [{"check": c["id"], "findings": c["findings"]} for c in operating["checks"]
                                  if c["severity"] == "error" and c["status"] == "fail"]}
    try:
        gates = export_gate_schedule(trial)
        summary["gates"] = "pass"
        summary["stations"] = [{k: v for k, v in city.items() if k != "claims"}
                                for city in gates["cities"] if city["code"] in ("SFB", "JAX", "BHM")]
        stands = [claim for city in gates["cities"] for claim in city["claims"] if claim["rowType"] == "stand"]
        summary["standClaims"] = len(stands)
        summary["standMinutes"] = sum(claim["end"] - claim["start"] for claim in stands)
    except GateCapacityError as error:
        summary["gates"] = "fail"
        summary["gateFailure"] = str(error)
    return summary, trial


def demand_details(search, plans):
    trial = apply_optimization_overlay(search.base, overlay(search, plans))
    options = search.screen.enumerate(trial["legs"])
    loads, records = search.screen.allocate(options)
    baseline_ids = set(search.legs)
    result = []
    for leg in trial["legs"]:
        if leg["id"] in baseline_ids:
            continue
        connection_od = Counter()
        group_demand = Counter()
        feed_flights = set()
        for record in records[leg["id"]]:
            connection_od[record["origin"], record["destination"]] += record["opportunity"]
            endpoint = record["origin"] if leg["destination"] == "SFB" else record["destination"]
            group_demand[search.screen.cities[endpoint]["group"]] += record["opportunity"]
            position = record["legs"].index(leg["id"])
            if leg["destination"] == "SFB" and position:
                feed_flights.add(record["legs"][position - 1])
            elif leg["origin"] == "SFB" and position < len(record["legs"]) - 1:
                feed_flights.add(record["legs"][position + 1])
        result.append({**leg, "departureClock": clock(leg["departureMinute"]),
                       "arrivalClock": clock(leg["arrivalMinute"]),
                       "local": loads[leg["id"]]["local"],
                       "connecting": sum(value for side, value in loads[leg["id"]].items() if side != "local"),
                       "total": sum(loads[leg["id"]].values()),
                       "oneStopConnecting": sum(r["opportunity"] for r in records[leg["id"]] if r["stops"] == 1),
                       "twoStopConnecting": sum(r["opportunity"] for r in records[leg["id"]] if r["stops"] == 2),
                       "topConnectingMarkets": [{"origin": a, "destination": b, "opportunity": value}
                                                for (a, b), value in connection_od.most_common(10)],
                       "connectingGroups": dict(group_demand),
                       "connectingFlights": [{"flight": search.legs[identifier]["flight"],
                                              "origin": search.legs[identifier]["origin"],
                                              "destination": search.legs[identifier]["destination"],
                                              "departure": search.legs[identifier]["departure"],
                                              "arrival": search.legs[identifier]["arrival"]}
                                             for identifier in sorted(feed_flights)]})
    return result


def preferred_analysis(search):
    # Exact 150-minute away-turn edge preserves BHM's 21:15 OKC connection.
    # These are trial clocks, not authorized schedule additions.
    plans = [
        {"route": 702, "hub": "JAX", "legs": [search.leg("SFB", "JAX", 1205, "MAX9"),
                                               search.leg("JAX", "SFB", 1293, "MAX9")]},
        {"route": 704, "hub": "BHM", "legs": [search.leg("SFB", "BHM", 1219, "MAX9"),
                                               search.leg("BHM", "SFB", 1395, "MAX9")]},
    ]
    return {"plans": plans, "strictValidation": validate(search, plans)[0],
            "hypotheticalBankExceptionValidation": validate(search, plans, True)[0],
            "demand": demand_details(search, plans)}


def main():
    base = read_json(ROOT / "data/schedules/schedule_7_v1_2_1/canonical_schedule.json")
    search = HoldSearch(base)
    searches = []
    for route in (702, 704):
        sequence = sorted((leg for leg in base["legs"] if leg["route"] == route),
                          key=lambda leg: leg["sequenceWithinRoute"])
        earliest = sequence[-1]["arrivalMinute"] + 40
        for hub in ("JAX", "BHM"):
            plans = []
            for departure in search.grid(earliest, 1260):
                outward = search.leg("SFB", hub, departure, "MAX9")
                # Short turn first; extended away holds are separately identifiable.
                for back in search.grid(outward["arrivalMinute"] + 40,
                                        min(1410, outward["arrivalMinute"] + 240)):
                    returning = search.leg(hub, "SFB", back, "MAX9")
                    legs = [outward, returning]
                    if not search.spacing(legs):
                        continue
                    score, values = search.score(legs)
                    plans.append({"route": route, "hub": hub, "legs": legs,
                                  "score": score, "legScores": values,
                                  "hubHoldMinutes": back - outward["arrivalMinute"]})
            plans.sort(key=lambda plan: -plan["score"])
            selected = [plans[0], next(p for p in plans if p["hubHoldMinutes"] <= 150)]
            earliest_plan = min(plans, key=lambda p: (p["legs"][1]["arrivalMinute"], p["legs"][0]["departureMinute"]))
            selected.append(earliest_plan)
            tested = []
            seen = set()
            for plan in selected:
                key = tuple(leg["departureMinute"] for leg in plan["legs"])
                if key in seen:
                    continue
                seen.add(key)
                strict, _ = validate(search, [plan])
                hypothetical = validate(search, [plan], True)[0] if hub == "JAX" else None
                tested.append({**plan, "strictValidation": strict,
                               "hypotheticalBankExceptionValidation": hypothetical,
                               "demand": demand_details(search, [plan])})
            searches.append({"route": route, "hub": hub, "existingTermination": sequence[-1]["arrival"],
                             "localOd": {"toHub": search.screen.od["SFB"][hub], "toSfb": search.screen.od[hub]["SFB"]},
                             "candidateTimings": len(plans), "tested": tested,
                             "topTimings": plans[:5]})
    combined = []
    for jax_route, bhm_route in ((702, 704), (704, 702)):
        jax = next(row for row in searches if row["route"] == jax_route and row["hub"] == "JAX")["tested"][0]
        bhm = next(row for row in searches if row["route"] == bhm_route and row["hub"] == "BHM")["tested"][0]
        plans = [jax, bhm]
        validation, _ = validate(search, plans, True)
        combined.append({"jaxRoute": jax_route, "bhmRoute": bhm_route,
                         "hypotheticalBankExceptionValidation": validation,
                         "demand": demand_details(search, plans)})
    report = {"baseline": base["schedule"]["id"], "workVersion": "1.2.2",
              "demandId": search.screen.demand_id,
              "interpretation": "Full-capture uncapped relative-choice opportunity units, not passenger loads, profit or net incremental demand. Existing schedule unchanged.",
              "search": "Five-minute departure grid plus earliest endpoints, 40-minute SFB turn, 40–240-minute hub hold, SFB departure through 21:00 and hub departure through 23:30. No existing flight retiming.",
              "searches": searches, "combined": combined, "preferred": preferred_analysis(search)}
    write_json(ROOT / "builds/schedule_7_v1_2_2_sfb_evenings.json", report)
    for row in searches:
        print(row["route"], row["hub"], "OD", row["localOd"])
        for plan in row["tested"]:
            print("  ", [(leg["departureClock"], leg["arrivalClock"], round(leg["local"], 1), round(leg["connecting"], 1))
                          for leg in plan["demand"]], "hold", plan["hubHoldMinutes"],
                  "errors", plan["strictValidation"]["operatingErrors"], "gates", plan["strictValidation"]["gates"],
                  "hypotheticalErrors", (plan["hypotheticalBankExceptionValidation"] or {}).get("operatingErrors"))
    for row in combined:
        print("Combined", row["jaxRoute"], row["bhmRoute"], row["hypotheticalBankExceptionValidation"])


if __name__ == "__main__":
    main()
