"""Review MCI destination overnights and B1 feed; never alter the working draft."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from caa_scheduler.io import read_json, write_json, sha256_file
from caa_scheduler.operating_validation import validate_operating_rules
from analyze_schedule_7_v1_2_1_holds import HoldSearch
from analyze_schedule_7_v1_2_3_bwi import make_overlay, validate, demand, retime
from analyze_schedule_7_v1_2_3_round_3 import audit
from analyze_schedule_7_v1_2_3_utilization import good
from analyze_schedule_7_v1_2_4 import cache_network
from analyze_schedule_7_v1_2_4_xna import maintenance
from review_crj200_line_alignment import routes, longest_gap

BASE = "data/schedules/schedule_7_v1_2_5_draft/canonical_schedule.json"
SCREEN = "config/proposals/schedule_7_v1_2_5_mci_screen.json"
REPORT = "config/proposals/schedule_7_v1_2_5_mci_review.json"


def inventory(base):
    rows = routes(base)
    grouped = {}
    for legs in rows.values():
        grouped.setdefault(legs[0]["line"], []).append(legs)
    result = []
    targets = set(base["operatingPolicy"]["ronTargetCities"])
    hubs = set(base["operatingPolicy"]["hubs"] + base["operatingPolicy"]["focusCities"])
    for line, days in sorted(grouped.items()):
        days.sort(key=lambda legs: legs[0]["day"])
        for current, following in zip(days, days[1:] + days[:1]):
            last, first = current[-1], following[0]
            if last["destination"] != "MCI":
                continue
            retained = [legs for legs in days if legs[0]["route"] != last["route"]]
            worst = longest_gap([legs[-1]["destination"] in targets and legs[0]["route"] != last["route"] for legs in days])
            result.append({"route": last["route"], "nextRoute": first["route"], "line": line,
                           "day": last["day"], "lineDays": len(days), "fleet": last["fleet"],
                           "terminator": last, "originator": first,
                           "maximumNonMxRunWithoutThisRon": worst,
                           "independentWithoutGrace": worst <= base["operatingPolicy"]["rollingRonWindowDays"]
                           and any(legs[-1]["destination"] in hubs for legs in retained),
                           "otherTargetRons": [{"route": legs[0]["route"], "city": legs[-1]["destination"]}
                                               for legs in retained if legs[-1]["destination"] in targets]})
    return result


def b1_view(base):
    bank = next(b for b in base["hubBanks"] if b["id"] == "MCI-B1")
    assigned = {a["legId"]: a["operation"] for a in base["bankAssignments"] if a["bankId"] == "MCI-B1"}
    incoming = [leg for leg in base["legs"] if assigned.get(leg["id"]) == "arrival"]
    outgoing = [leg for leg in base["legs"] if assigned.get(leg["id"]) == "departure"]
    return {"window": bank, "arrivals": [{**leg, "connectingB1Flights": [d["flight"] for d in outgoing
                            if d["destination"] != leg["origin"] and 30 <= d["departureMinute"] - leg["arrivalMinute"] <= 240]}
                            for leg in sorted(incoming, key=lambda leg: leg["arrivalMinute"])],
            "departures": [{**leg, "feedingB1Flights": [a["flight"] for a in incoming
                            if a["origin"] != leg["destination"] and 30 <= leg["departureMinute"] - a["arrivalMinute"] <= 240]}
                            for leg in sorted(outgoing, key=lambda leg: (leg["departureMinute"], leg["flight"]))]}


def departure_demand(base, loads, records=None):
    result = [{"flight": leg["flight"], "id": leg["id"], "destination": leg["destination"], "departure": leg["departure"],
             "local": loads[leg["id"]]["local"],
             "connecting": sum(value for kind, value in loads[leg["id"]].items() if kind != "local"),
             "total": sum(loads[leg["id"]].values())} for leg in b1_view(base)["departures"]]
    legs = {leg["id"]: leg for leg in base["legs"]}
    for row in result:
        origins, inbound_opportunity = set(), 0
        for record in (records or {}).get(row["id"], []):
            index = record["legs"].index(row["id"])
            if index and record["opportunity"] > 0:
                previous = legs[record["legs"][index - 1]]
                if previous["destination"] == "MCI":
                    origins.add(previous["origin"])
                    inbound_opportunity += record["opportunity"]
        row.update(effectiveInboundFeedCities=sorted(origins), inboundConnectingOpportunity=inbound_opportunity)
        row.pop("id")
    return result


def screen(search):
    base = search.base
    rons = inventory(base)
    candidates = []
    destinations = [city for city in search.screen.cities if city not in search.screen.hubs
                    and 0 <= len(search.pairs["MCI", city]) <= 3]
    bank = b1_view(base)
    for row in rons:
        last, first, fleet = row["terminator"], row["originator"], row["fleet"]
        for city in destinations:
            returning = search.leg(city, "MCI", 270, fleet)
            arrival = returning["arrivalMinute"]
            shift = max(0, arrival + 40 - first["departureMinute"])
            if arrival > 335 or shift > 35:
                continue
            choices = []
            for departure in range(((last["arrivalMinute"] + 44) // 5) * 5, 1395, 5):
                outgoing = search.leg("MCI", city, departure, fleet)
                if outgoing["arrivalMinute"] > 1441 or search.bank("MCI", departure) is None:
                    continue
                if not search.spacing([outgoing, returning]):
                    continue
                score, values = search.score([outgoing, returning])
                choices.append({"city": city, "eveningDepartureMinute": departure,
                                "eveningArrivalMinute": outgoing["arrivalMinute"], "morningDepartureMinute": 270,
                                "morningArrivalMinute": arrival, "originatorDelayMinutes": shift,
                                "currentFlightsEachWay": len(search.pairs["MCI", city]),
                                "screenOpportunity": score, "eveningOpportunity": values[0], "morningOpportunity": values[1],
                                "existingB1FlightsFed": [leg["flight"] for leg in bank["departures"]
                                     if leg["destination"] != city and 30 <= leg["departureMinute"] - arrival <= 240],
                                "earliestUsefulOutboundMinute": arrival + 30,
                                "earliestAircraftOutboundMinute": arrival + 40,
                                "minimumBankShiftForAircraftDeparture": max(0, first["departureMinute"] + shift - 344),
                                "maintenanceIndependent": row["independentWithoutGrace"]})
            if choices:
                best = max(choices, key=lambda item: item["screenOpportunity"])
                candidates.append({"route": row["route"], "nextRoute": row["nextRoute"], "line": row["line"],
                                   "fleet": fleet, **best})
    report = {"status": "analysis only; draft unchanged", "baseCanonical": BASE, "baseSha256": sha256_file(ROOT / BASE),
              "b1": bank, "mciRons": rons, "candidates": sorted(candidates, key=lambda item: -item["screenOpportunity"]),
              "scope": "MCI markets with 0–3 daily flights, including new pairings; returns at 04:30 local; arrival by 00:01 local; "
                       "originator delay at most 35 minutes. Screen scores are not full-joint demand or validation.",
              "model": "Pinned BTS O-D, seat-uncapped relative-choice one/two-stop opportunities; not forecasts or loads."}
    write_json(ROOT / SCREEN, report)
    for candidate in report["candidates"][:30]:
        print(candidate["route"], candidate["nextRoute"], candidate["fleet"], candidate["city"],
              "score", round(candidate["screenOpportunity"], 1), "back", candidate["morningArrivalMinute"],
              "delay", candidate["originatorDelayMinutes"], "fed", len(candidate["existingB1FlightsFed"]),
              "independent", candidate["maintenanceIndependent"], flush=True)


def build_overlay(search, name, plans, *, bank_shift=0, move_dsm=False, b1_wave=None, connect_aus=False):
    rows = routes(search.base)
    additions, changes = [], []
    for terminator, originator, city, departure in plans:
        fleet = rows[terminator][0]["fleet"]
        additions.extend([{"route": terminator, "legs": [search.leg("MCI", city, departure, fleet)]},
                          {"route": originator, "legs": [search.leg(city, "MCI", 270, fleet)]}])
        returning = additions[-1]["legs"][0]
        shift = max(0, returning["arrivalMinute"] + 40 - rows[originator][0]["departureMinute"])
        changes.extend(retime(search, originator, [shift]))
    if bank_shift:
        # Keep the early AUS flight in the shifted bank without a new exception.
        changes.extend(retime(search, 713, [bank_shift, max(0, bank_shift - 3)]))
        ind_shift = max(0, 285 + bank_shift - 295)
        if ind_shift:
            changes.extend(retime(search, 504, [ind_shift, ind_shift]))
    if b1_wave is not None:
        # Preserve PGD and JAX: their immediate turns make a broad delay cascade.
        for route in (716, 510, 337, 113, 114, 146, 155, 136):
            first = rows[route][0]
            changes.extend(retime(search, route, [b1_wave - first["departureMinute"]]))
    if connect_aus:
        changes.extend(retime(search, 713, [65, 62, 9]))
        changes.extend(retime(search, 710, [37]))
    changes = list({change["legId"]: change for change in changes}.values())
    change = make_overlay(search, additions, retimings=changes)
    change["id"] = "v1.2.5-mci-" + name
    change["baseSchedule"].update(canonical=BASE, sha256=sha256_file(ROOT / BASE))
    change["schedule"].update(id="schedule_7_v1_2_5_mci_" + name, version="1.2.5-analysis",
                              label="Unpublished v1.2.5 MCI B1 proposal " + name)
    remap = {leg["id"]: leg["id"].replace("V123-", "V125-MCI-" + name + "-") for leg in change["insertLegs"]}
    for leg in change["insertLegs"]:
        leg["id"] = remap[leg["id"]]
    for assignment in change["bankAssignmentsToAdd"]:
        assignment["legId"] = remap[assignment["legId"]]
    if bank_shift:
        change["hubBankChanges"] = [{"bankId": "MCI-B1", "expectedStartMinute": 285,
                                    "expectedEndMinute": 345, "startMinute": 285 + bank_shift,
                                    "endMinute": 345 + bank_shift}]
    for leg in change["insertLegs"]:
        if leg["destination"] == "MCI" and not any(a["legId"] == leg["id"] and a["operation"] == "arrival"
                                                    for a in change["bankAssignmentsToAdd"]):
            change["bankAssignmentsToAdd"].append({"legId": leg["id"], "operation": "arrival", "bankId": "MCI-B1"})
    if move_dsm:
        leg = next(leg for leg in rows[153] if leg["flight"] == 1733)
        change["legReassignments"] = [{"legId": leg["id"], "expectedRoute": 153,
                                      "expectedSequenceWithinRoute": leg["sequenceWithinRoute"], "targetRoute": 154}]
        change["retimeLegs"].append({"legId": leg["id"], "expectedDepartureMinute": leg["departureMinute"],
                                    "expectedArrivalMinute": leg["arrivalMinute"], "departureMinute": 335,
                                    "arrivalMinute": 385})
        change["bankAssignmentReplacements"].append({"legId": leg["id"], "operation": "departure", "bankId": "MCI-B1"})
    change["approval"] = {"status": "reviewed proposal only; not implemented",
                          "publication": "Reserved to user decision", "scope": "MCI overnight feeders; " + name}
    return change


def review(search, name, plans, **kwargs):
    change = build_overlay(search, name, plans, **kwargs)
    validation, trial = validate(search, change)
    # Standing authorization allows geographically useful additional hub service.
    # Record the precise service-tier exception in the proposal; waive no timing,
    # physical, maintenance or spacing rule.
    tier_findings = [finding for check in validation["blocking"] if check["check"] == "tiered_service_minimums"
                     for finding in check["findings"]]
    for finding in tier_findings:
        change["operatingOverrides"].append({"checkId": "tiered_service_minimums", "findingId": finding["id"],
            "reason": "Standing user authorization permits useful additional hub coverage. MCI B1 analysis only; "
                      "physical, maintenance, spacing and timing rules remain enforced."})
    if tier_findings:
        validation, trial = validate(search, change)
    validation.pop("affectedStations", None)
    result = {"id": name, "plans": plans, "validation": validation, "retimings": change["retimeLegs"],
              "bankChanges": change.get("hubBankChanges", []), "maintenance": {line: maintenance(trial, line)
              for line in sorted({routes(trial)[plan[0]][0]["line"] for plan in plans})}}
    for detail in result["maintenance"].values():
        detail.pop("longestRun", None)
    print("VALIDATE", name, validation, flush=True)
    if good(validation):
        result["demand"] = demand(search, trial, {leg["id"] for leg in change["insertLegs"]})
        result["connectionAudit"] = audit(search, trial)
        options = search.screen.enumerate(trial["legs"])
        loads, records = search.screen.allocate(options)
        result["changedFlightConnections"] = []
        for timing in change["retimeLegs"]:
            identifier = timing["legId"]
            before = {tuple(record["legs"]) for record in search.screen.connections[identifier]}
            after = {tuple(record["legs"]) for record in records[identifier]}
            result["changedFlightConnections"].append({"flight": search.legs[identifier]["flight"],
                "lostConnectingChoices": len(before-after), "addedConnectingChoices": len(after-before),
                "oldOpportunity": sum(search.screen.loads[identifier].values()), "newOpportunity": sum(loads[identifier].values())})
        result["b1"] = b1_view(trial)
        result["b1DepartureDemand"] = departure_demand(trial, loads, records)
        for flight in result["demand"]["flights"]:
            references = flight.pop("connectingFlights")
            flight.update(connectingFlightCount=len(references), connectingFlightNumbers=[leg["flight"] for leg in references])
            flight["topMarkets"] = flight["topMarkets"][:5]
        baseline_op = validate_operating_rules(search.base)
        trial_op = validate_operating_rules(trial)
        result["newWarningFindings"], result["revisedWarningFindings"] = [], []
        for check in trial_op["checks"]:
            if check["severity"] != "warning":
                continue
            previous = {finding["id"]: finding for old in baseline_op["checks"] if old["id"] == check["id"]
                        for finding in old["findings"]}
            for finding in check["findings"]:
                if finding["id"] not in previous:
                    result["newWarningFindings"].append({"check": check["id"], **finding})
                elif finding != previous[finding["id"]]:
                    result["revisedWarningFindings"].append({"check": check["id"], "before": previous[finding["id"]],
                                                            "after": finding})
        result["flightPreservation"] = {"baseFlights": len(search.base["legs"]), "trialFlights": len(trial["legs"]),
            "fleetInventoryUnchanged": trial["schedule"]["fleetCounts"] == search.base["schedule"]["fleetCounts"]}
        original = {leg["id"]: leg for leg in search.base["legs"]}
        actual = {leg["id"]: leg for leg in trial["legs"]}
        mutable = {timing["legId"] for timing in change["retimeLegs"]}
        reassigned = {mapping["legId"] for mapping in change.get("legReassignments", [])}
        for identifier, leg in original.items():
            assert identifier in actual
            assert all(actual[identifier][key] == leg[key] for key in ("flight", "origin", "destination", "fleet"))
            if identifier not in mutable:
                assert all(actual[identifier][key] == leg[key] for key in ("departureMinute", "arrivalMinute"))
            if identifier not in reassigned:
                assert all(actual[identifier][key] == leg[key] for key in ("route", "line", "day"))
        assert trial["operatingPolicy"]["overrides"] == search.base["operatingPolicy"]["overrides"] + change["operatingOverrides"]
        result["flightPreservation"].update(unchangedBaseFlightClocks=len(original) - len(mutable),
                                            baseRouteIdentitiesPreserved=not reassigned,
                                            checks="pass")
        write_json(ROOT / ("builds/mci-b1-review/" + name + "-canonical.json"), trial)
        print("DEMAND", name, [(leg["origin"]+"-"+leg["destination"], round(leg["total"],1))
              for leg in result["demand"]["flights"]], result["connectionAudit"], flush=True)
    write_json(ROOT / ("config/proposals/schedule_7_v1_2_5_mci_" + name.lower() + ".json"), change)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["screen", "review"])
    parser.add_argument("--cases", nargs="*", help="Review only named cases; preserve completed other reviews")
    args = parser.parse_args()
    search = HoldSearch(read_json(ROOT / BASE))
    cache_network(search)
    if args.mode == "screen":
        screen(search)
        return
    report = {"status": "reviewed proposals only; v1.2.5 draft and app unchanged", "baseCanonical": BASE,
              "baseSha256": sha256_file(ROOT / BASE), "baselineB1": b1_view(search.base),
              "baselineB1DepartureDemand": departure_demand(search.base, search.screen.loads, search.screen.connections),
              "model": "Pinned BTS O-D; seat-uncapped relative-choice one/two-stop opportunity units, not passengers, loads or profit.",
              "candidates": []}
    cases = [
        ("SBN_112", [(112, 113, "SBN", 1245)], {}),
        ("SBN_135", [(135, 136, "SBN", 1275)], {}),
        ("SDF_135", [(135, 136, "SDF", 1275)], {"bank_shift": 1}),
        ("SDF_715", [(715, 716, "SDF", 1280)], {}),
        ("SBN_715", [(715, 716, "SBN", 1280)], {}),
        ("SBN112_SDF715", [(112, 113, "SBN", 1245), (715, 716, "SDF", 1280)], {}),
        ("SBN112_SDF135", [(112, 113, "SBN", 1245), (135, 136, "SDF", 1275)], {"bank_shift": 1}),
        ("SDF112_SBN715", [(112, 113, "SDF", 1245), (715, 716, "SBN", 1280)], {"bank_shift": 1}),
        ("SBN154_MX153", [(154, 155, "SBN", 1280)], {"move_dsm": True}),
        ("SBN145_MX153", [(145, 146, "SBN", 1245)], {"move_dsm": True}),
        ("SBN112_SDF135_OPT", [(112, 113, "SBN", 1270), (135, 136, "SDF", 1275)], {"bank_shift": 1}),
        ("SDF112_SBN135_OPT", [(112, 113, "SDF", 1270), (135, 136, "SBN", 1275)], {"bank_shift": 1}),
        ("SBN112_SDF135_SGF323", [(112, 113, "SBN", 1270), (135, 136, "SDF", 1275),
                                  (323, 324, "SGF", 1390)], {"bank_shift": 6, "b1_wave": 350}),
        ("SBN112_SDF135_DSM323", [(112, 113, "SBN", 1270), (135, 136, "SDF", 1275),
                                  (323, 324, "DSM", 1390)], {"bank_shift": 7, "b1_wave": 351}),
        ("GRR715", [(715, 716, "GRR", 1280)], {"bank_shift": 1}),
        ("SDF112_SBN135_GRR715", [(112, 113, "SDF", 1270), (135, 136, "SBN", 1275),
                                 (715, 716, "GRR", 1280)], {"bank_shift": 1}),
        ("SDF112_SBN135_GRR715_SGF323", [(112, 113, "SDF", 1270), (135, 136, "SBN", 1275),
                                 (715, 716, "GRR", 1280), (323, 324, "SGF", 1390)],
                                 {"bank_shift": 6, "b1_wave": 350}),
        ("FWA135", [(135, 136, "FWA", 1275)], {"bank_shift": 5}),
        ("SBN507", [(507, 508, "SBN", 1290)], {}),
        ("SDF507", [(507, 508, "SDF", 1270)], {}),
        ("FOUR_BUFFERED", [(112, 113, "SDF", 1270), (135, 136, "SBN", 1285),
                            (715, 716, "GRR", 1283), (323, 324, "SGF", 1390)],
                            {"bank_shift": 6, "b1_wave": 350}),
        ("FOUR_ALL_CONNECT", [(112, 113, "SDF", 1270), (135, 136, "SBN", 1285),
                              (715, 716, "GRR", 1283), (323, 324, "SGF", 1390)],
                              {"bank_shift": 6, "b1_wave": 350, "connect_aus": True}),
    ]
    if args.cases and (ROOT / REPORT).exists():
        report = read_json(ROOT / REPORT)
        assert report["baseSha256"] == sha256_file(ROOT / BASE), "Stale review"
        report["baselineB1DepartureDemand"] = departure_demand(search.base, search.screen.loads, search.screen.connections)
    for name, plans, kwargs in cases:
        if args.cases and name not in args.cases:
            continue
        report["candidates"] = [candidate for candidate in report["candidates"] if candidate["id"] != name]
        report["candidates"].append(review(search, name, plans, **kwargs))
        write_json(ROOT / REPORT, report)
    assert sha256_file(ROOT / BASE) == report["baseSha256"], "Working draft changed"
    old_warnings = {check["id"]: {finding["id"]: finding for finding in check["findings"]}
                    for check in validate_operating_rules(search.base)["checks"] if check["severity"] == "warning"}
    for candidate in report["candidates"]:
        if "newWarningFindings" not in candidate or "revisedWarningFindings" in candidate:
            continue
        new, revised = [], []
        for finding in candidate["newWarningFindings"]:
            check = finding["check"]
            previous = old_warnings.get(check, {}).get(finding["id"])
            if previous is None:
                new.append(finding)
            else:
                revised.append({"check": check, "before": previous,
                                "after": {key: value for key, value in finding.items() if key != "check"}})
        candidate.update(newWarningFindings=new, revisedWarningFindings=revised)
    report.update(recommendedCandidate="FOUR_BUFFERED", lowerDisruptionCandidate="SDF112_SBN135_GRR715",
                  decision={"recommendation": "SDF on 112/113, SBN on 135/136, GRR on 715/716, SGF on 323/324; "
                            "shift B1 six minutes and eight 05:35 departures fifteen minutes. Preserve all later clocks "
                            "except the three-minute AUS return adjustment.",
                            "fullyConnectingAus": "Defer: the tested 05:50 AUS originator and downstream retimings "
                            "lose all connections in five markets (61.1 underlying O-D units). An earlier AUS departure "
                            "can use IND but still misses the existing TUL connection; repairing TUL's turn cascades into SYR bank timing.",
                            "maintenanceRealignment": "Retain both AI MCI RONs. Moving the 153 DSM terminator to 154's morning "
                            "passes maintenance but worsens DSM coverage and loses OKC-DSM's valid connection.",
                            "dsmInsteadOfSgf": "Higher modeled demand, but fourth MCI frequency. SGF gets its second and broadens "
                            "the bank's geographic inbound feed."})
    recommended = "config/proposals/schedule_7_v1_2_5_mci_four_buffered.json"
    if (ROOT / recommended).exists():
        report.update(recommendedOverlay=recommended, recommendedOverlaySha256=sha256_file(ROOT / recommended))
    write_json(ROOT / REPORT, report)


if __name__ == "__main__":
    main()
