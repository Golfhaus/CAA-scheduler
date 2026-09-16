from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable

from .gate_export import _capacity
from .gates import (
    GateClaim,
    apply_forced_stand_splits,
    assign_gates,
    build_claims,
    overlaps,
)


def _finding(
    finding_id: str, message: str, **evidence: Any
) -> dict[str, Any]:
    return {"id": finding_id, "message": message, "evidence": evidence}


def _check(
    check_id: str,
    title: str,
    section: str,
    severity: str,
    findings: Iterable[dict[str, Any]],
    pass_message: str,
    *,
    metrics: dict[str, Any] | None = None,
    hard_stop: bool = False,
) -> dict[str, Any]:
    items = list(findings)
    return {
        "id": check_id,
        "title": title,
        "section": section,
        "severity": severity,
        "hardStop": hard_stop,
        "status": "pass" if not items else ("fail" if severity == "error" else "warning"),
        "message": pass_message if not items else f"{len(items)} finding(s)",
        "metrics": metrics or {},
        "findings": items,
    }


def _not_evaluated(
    check_id: str,
    title: str,
    section: str,
    reason: str,
    missing: list[str],
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "section": section,
        "severity": "warning",
        "hardStop": False,
        "status": "not_evaluated",
        "message": reason,
        "metrics": {"missingInputs": missing},
        "findings": [],
    }


def _routes(canonical: dict[str, Any]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: defaultdict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for leg in canonical["legs"]:
        grouped[(leg["line"], leg["day"])].append(leg)
    for legs in grouped.values():
        legs.sort(key=lambda leg: leg["sequenceWithinRoute"])
    return dict(grouped)


def _cyclic_gaps(values: list[int | float]) -> list[dict[str, int | float]]:
    ordered = sorted(values)
    if not ordered:
        return []
    if len(ordered) == 1:
        return [{"from": ordered[0], "to": ordered[0], "minutes": 1440}]
    return [
        {
            "from": start,
            "to": ordered[(index + 1) % len(ordered)],
            "minutes": (ordered[(index + 1) % len(ordered)] - start) % 1440,
        }
        for index, start in enumerate(ordered)
    ]


def _apply_overrides(
    checks: list[dict[str, Any]], policy: dict[str, Any], schedule_number: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    overrides = policy.get("overrides", [])
    by_key = {
        (override["checkId"], override["findingId"]): override
        for override in overrides
        if override.get("expiresAfterSchedule") is None
        or schedule_number <= override["expiresAfterSchedule"]
    }
    used: set[tuple[str, str]] = set()
    for check in checks:
        for finding in check["findings"]:
            key = (check["id"], finding["id"])
            override = by_key.get(key)
            if override and not check["hardStop"]:
                finding["override"] = {
                    "reason": override["reason"],
                    "approvedBy": override.get("approvedBy"),
                    "expiresAfterSchedule": override.get("expiresAfterSchedule"),
                }
                used.add(key)
        effective = [finding for finding in check["findings"] if "override" not in finding]
        check["metrics"]["findingCount"] = len(check["findings"])
        check["metrics"]["effectiveFindingCount"] = len(effective)
        check["metrics"]["overriddenFindingCount"] = len(check["findings"]) - len(effective)
        if check["findings"] and not effective:
            check["status"] = "overridden"
            check["message"] = f"All {len(check['findings'])} finding(s) have explicit overrides"

    unused = [
        override
        for override in overrides
        if (override["checkId"], override["findingId"]) not in used
    ]
    return checks, unused


def validate_operating_rules(canonical: dict[str, Any]) -> dict[str, Any]:
    policy = canonical.get("operatingPolicy")
    if not policy:
        raise ValueError("Canonical schedule does not contain operatingPolicy")

    legs = canonical["legs"]
    cities = canonical["cities"]
    routes = _routes(canonical)
    city_by_code = {city["code"]: city for city in cities}
    hubs = set(policy["hubs"])
    focus_cities = set(policy["focusCities"])
    hubs_or_focus = hubs | focus_cities
    checks: list[dict[str, Any]] = []

    served = {
        code for leg in legs for code in (leg["origin"], leg["destination"])
    }
    active = {city["code"] for city in cities if city["active"]}
    missing_service = sorted(active - served)
    checks.append(
        _check(
            "destination_coverage",
            "Active-city coverage",
            "§1.8",
            "error",
            (
                _finding(code, f"Active city {code} has no scheduled service", city=code)
                for code in missing_service
            ),
            "Every active city has scheduled service",
            metrics={"activeCities": len(active), "servedActiveCities": len(active & served)},
        )
    )

    fleet_counts = canonical["schedule"].get("fleetCounts", {})
    fleet_days: defaultdict[str, set[tuple[str, int]]] = defaultdict(set)
    for leg in legs:
        fleet_days[leg["fleet"]].add((leg["line"], leg["day"]))
    fleet_findings = []
    for fleet, used in sorted(fleet_days.items()):
        capacity = fleet_counts.get(fleet)
        if capacity is None:
            fleet_findings.append(
                _finding(
                    fleet,
                    f"Fleet {fleet} has no count in this schedule's fleet plan",
                    fleet=fleet,
                    used=len(used),
                )
            )
        elif len(used) > capacity:
            fleet_findings.append(
                _finding(
                    fleet,
                    f"{fleet} uses {len(used)} aircraft-days against a cap of {capacity}",
                    fleet=fleet,
                    used=len(used),
                    capacity=capacity,
                )
            )
    checks.append(
        _check(
            "fleet_capacity",
            "Fleet aircraft-day capacity",
            "§1.4 / §1.6a",
            "error",
            fleet_findings,
            "Every fleet is within its aircraft-day cap",
            metrics={
                fleet: {"used": len(fleet_days[fleet]), "capacity": capacity}
                for fleet, capacity in fleet_counts.items()
            },
        )
    )

    windows = policy["departureWindows"]
    curfew_findings = []
    red_eye_count = 0
    for leg in legs:
        departure = leg["departureMinute"] % 1440
        arrival = leg["arrivalMinute"] % 1440
        latest = (
            windows["hubOrFocusLatestMinute"]
            if leg["origin"] in hubs_or_focus
            else windows["destinationLatestMinute"]
        )
        normal = windows["earliestMinute"] <= departure <= latest
        red_eye = (
            (departure > windows["destinationLatestMinute"] or departure <= windows["redEyeLatestMinute"])
            and windows["redEyeArrivalMinimumMinute"]
            <= arrival
            <= windows["redEyeArrivalMaximumMinute"]
        )
        if red_eye:
            red_eye_count += 1
        if not normal and not red_eye:
            curfew_findings.append(
                _finding(
                    str(leg["flight"]),
                    f"Flight {leg['flight']} departs {leg['origin']} outside its allowed window",
                    flight=leg["flight"],
                    origin=leg["origin"],
                    destination=leg["destination"],
                    departureMinute=departure,
                    arrivalMinute=arrival,
                    normalWindow=[windows["earliestMinute"], latest],
                )
            )
    checks.append(
        _check(
            "departure_windows",
            "Departure windows and curfews",
            "§2.5 / Lesson 32",
            "error",
            curfew_findings,
            "Every departure is inside a normal window or valid red-eye window",
            metrics={"redEyes": red_eye_count},
            hard_stop=True,
        )
    )

    continuity_findings = []
    for line in sorted({line for line, _ in routes}):
        days = sorted(day for candidate, day in routes if candidate == line)
        for day, next_day in zip(days, days[1:] + days[:1]):
            current = routes[(line, day)][-1]
            following = routes[(line, next_day)][0]
            if current["destination"] != following["origin"]:
                continuity_findings.append(
                    _finding(
                        f"{line}-{day}-{next_day}",
                        f"Line {line} ends day {day} at {current['destination']} but starts day {next_day} at {following['origin']}",
                        line=line,
                        day=day,
                        nextDay=next_day,
                        terminator=current["destination"],
                        originator=following["origin"],
                    )
                )
    checks.append(
        _check(
            "line_day_continuity",
            "Line continuity across operating days",
            "§2.8 / Lesson 29",
            "error",
            continuity_findings,
            "Every line closes continuously across days, including wraparound",
        )
    )

    short_turns = []
    long_turns = []
    minimum_turn = policy["turns"]["minimumMinutes"]
    hold_threshold = policy["turns"]["holdThresholdMinutes"]
    for (line, day), route_legs in routes.items():
        for arriving, departing in zip(route_legs, route_legs[1:]):
            # Canonical clock minutes are local to the station and a valid
            # 03:00-to-03:00 route day can cross midnight.  Both touches are
            # at the same station, so the cyclic local-clock gap is the
            # authoritative turn duration.
            duration = (
                departing["departureMinute"] - arriving["arrivalMinute"]
            ) % 1440
            details = {
                "line": line,
                "day": day,
                "city": arriving["destination"],
                "arrivalFlight": arriving["flight"],
                "departureFlight": departing["flight"],
                "minutes": duration,
            }
            finding_id = f"{line}-{day}-{arriving['flight']}-{departing['flight']}"
            if duration < minimum_turn:
                short_turns.append(
                    _finding(finding_id, f"Turn at {arriving['destination']} is {duration:g} minutes", **details)
                )
            elif duration > hold_threshold:
                long_turns.append(
                    _finding(
                        finding_id,
                        f"Hold at {arriving['destination']} is {duration:g} minutes and needs deliberate-hold review",
                        **details,
                    )
                )
    checks.append(
        _check(
            "minimum_turn_time",
            "Minimum same-day turn time",
            "§2.5",
            "error",
            short_turns,
            f"Every same-day turn is at least {minimum_turn} minutes",
        )
    )
    checks.append(
        _check(
            "long_hold_review",
            "Long same-day holds",
            "§1.6a / §2.5",
            "warning",
            long_turns,
            f"No same-day hold exceeds {hold_threshold} minutes without review",
        )
    )

    line_counts = Counter(line for line, _ in routes)
    line_count_findings = [
        _finding(
            line,
            f"Line {line} contains {count} routes; the standing guideline is 9–12",
            line=line,
            routes=count,
            guideline=[9, 12],
        )
        for line, count in sorted(line_counts.items())
        if not 9 <= count <= 12
    ]
    checks.append(
        _check(
            "line_route_count",
            "Routes per line",
            "§2.8",
            "warning",
            line_count_findings,
            "Every line contains 9–12 routes",
        )
    )

    ron_targets = set(policy["ronTargetCities"])
    rolling_limit = policy["rollingRonWindowDays"]
    grace = policy["rollingRonGraceDays"]
    rolling_errors = []
    rolling_grace = []
    for line in sorted(line_counts):
        days = sorted(day for candidate, day in routes if candidate == line)
        target_flags = [routes[(line, day)][-1]["destination"] in ron_targets for day in days]
        if all(target_flags):
            longest = 0
        elif not any(target_flags):
            longest = len(target_flags)
        else:
            doubled = target_flags + target_flags
            longest = current = 0
            for flag in doubled:
                current = 0 if flag else current + 1
                longest = max(longest, current)
            longest = min(longest, len(target_flags))
        details = {"line": line, "longestRunWithoutTargetRon": longest, "limit": rolling_limit, "grace": grace}
        if longest > rolling_limit + grace:
            rolling_errors.append(
                _finding(line, f"Line {line} has {longest} consecutive days without a target-city RON", **details)
            )
        elif longest > rolling_limit:
            rolling_grace.append(
                _finding(line, f"Line {line} uses the one-day rolling RON grace", **details)
            )
    checks.append(
        _check(
            "rolling_ron_window",
            "Rolling target-city RON window",
            "§2.1 / Lesson 31",
            "error",
            rolling_errors,
            f"Every line reaches a target RON within {rolling_limit + grace} days",
        )
    )
    checks.append(
        _check(
            "rolling_ron_grace",
            "Rolling RON grace usage",
            "Lesson 31",
            "warning",
            rolling_grace,
            "No line uses the standing one-day grace",
        )
    )

    terminators = Counter(route_legs[-1]["destination"] for route_legs in routes.values())
    ron_exemptions = set(policy.get("destinationRonExemptions", []))
    no_destination_ron = [
        city["code"]
        for city in cities
        if city["active"]
        and city["role"] == "destination"
        and city["code"] not in ron_exemptions
        and terminators[city["code"]] == 0
    ]
    checks.append(
        _check(
            "destination_ron_coverage",
            "Destination RON coverage",
            "§1.6a / §2.3",
            "error",
            (
                _finding(code, f"Destination {code} has no terminating route", city=code, terminators=0)
                for code in no_destination_ron
            ),
            "Every non-exempt destination has at least one terminating route",
        )
    )

    p2p = [
        leg
        for leg in legs
        if leg["origin"] not in hubs_or_focus
        and leg["destination"] not in hubs_or_focus
    ]
    p2p_share = len(p2p) / len(legs) if legs else 0
    p2p_findings = []
    if p2p_share > policy["pointToPointMaximumShare"]:
        p2p_findings.append(
            _finding(
                "network",
                f"Point-to-point flying is {p2p_share:.2%}, above the {policy['pointToPointMaximumShare']:.0%} cap",
                pointToPointFlights=len(p2p),
                totalFlights=len(legs),
                share=p2p_share,
                maximumShare=policy["pointToPointMaximumShare"],
            )
        )
    checks.append(
        _check(
            "point_to_point_share",
            "Point-to-point flight share",
            "§2.4",
            "error",
            p2p_findings,
            "Point-to-point flying is within the 10% cap",
            metrics={"flights": len(p2p), "totalFlights": len(legs), "share": p2p_share},
        )
    )

    pair_counts = Counter((leg["origin"], leg["destination"]) for leg in legs)
    market_cap = policy["marketMaximumDailyDeparturesPerDirection"]
    frequency_findings = [
        _finding(
            f"{origin}-{destination}",
            f"{origin}–{destination} has {count} daily departures against a cap of {market_cap}",
            origin=origin,
            destination=destination,
            departures=count,
            cap=market_cap,
        )
        for (origin, destination), count in sorted(pair_counts.items())
        if count > market_cap
    ]
    checks.append(
        _check(
            "market_frequency_ceiling",
            "Per-direction market frequency ceiling",
            "§2.7",
            "error",
            frequency_findings,
            f"No directed market exceeds {market_cap} daily departures",
        )
    )

    section26 = policy["section26"]
    station_departures = Counter(leg["origin"] for leg in legs)
    pair_departures: defaultdict[tuple[str, str], list[int | float]] = defaultdict(list)
    for leg in legs:
        pair_departures[(leg["origin"], leg["destination"])].append(leg["departureMinute"] % 1440)
    spacing_findings = []
    for (origin, destination), departures in sorted(pair_departures.items()):
        if len(departures) < 2:
            continue
        gaps = _cyclic_gaps(departures)
        if destination in hubs:
            target = section26["hardFloorMinutes"]
            allowed = 0
            violations = [gap for gap in gaps if gap["minutes"] < target]
        else:
            station_factor = math.sqrt(
                section26["stationReferenceDepartures"] / station_departures[origin]
            )
            station_factor = min(
                max(station_factor, section26["stationFactorMinimum"]),
                section26["stationFactorMaximum"],
            )
            target = min(
                max(
                    section26["numeratorMinutes"] / len(departures) * station_factor,
                    section26["hardFloorMinutes"],
                ),
                section26["pairingTargetMaximumMinutes"],
            )
            tolerance = target * section26["nearTargetTolerance"]
            allowed = 1 if len(departures) >= section26["oneExceptionMinimumFrequency"] else 0
            hard = [gap for gap in gaps if gap["minutes"] < section26["hardFloorMinutes"]]
            below_tolerance = [gap for gap in gaps if gap["minutes"] < tolerance]
            violations = hard or (below_tolerance if len(below_tolerance) > allowed else [])
        if violations:
            spacing_findings.append(
                _finding(
                    f"{origin}-{destination}",
                    f"{origin}–{destination} fails same-pairing spacing",
                    origin=origin,
                    destination=destination,
                    departures=sorted(departures),
                    gaps=gaps,
                    targetMinutes=target,
                    allowedExceptions=allowed,
                    hubBound=destination in hubs,
                )
            )
    checks.append(
        _check(
            "section_26_pairing_spacing",
            "Section 2.6 Check A — same-pairing spacing",
            "§2.6 Check A",
            "error",
            spacing_findings,
            "Every directed pairing satisfies its applicable spacing rule",
        )
    )

    maximum_gap = section26["maximumCityDepartureGapMinutes"]
    city_gap_findings = []
    for city, departures in sorted(
        (city, [leg["departureMinute"] % 1440 for leg in legs if leg["origin"] == city])
        for city in active
    ):
        gaps = _cyclic_gaps(departures)
        considered = (
            gaps
            if section26["includeOvernightWrapForCityDepartureGap"]
            else gaps[:-1]
        )
        excessive = [gap for gap in considered if gap["minutes"] > maximum_gap]
        if excessive:
            city_gap_findings.append(
                _finding(
                    city,
                    f"{city} has no departure for more than {maximum_gap} minutes",
                    city=city,
                    departures=sorted(departures),
                    excessiveGaps=excessive,
                    includesOvernightWrap=section26[
                        "includeOvernightWrapForCityDepartureGap"
                    ],
                )
            )
    checks.append(
        _check(
            "section_26_city_departure_gap",
            "Section 2.6 Check B — maximum city departure service gap",
            "§2.6 Check B",
            "warning",
            city_gap_findings,
            f"No city has a departure service gap over {maximum_gap} minutes",
        )
    )

    minimum_wrap_gap = 1440 - windows["hubOrFocusLatestMinute"] + windows["earliestMinute"]
    policy_conflicts = []
    if (
        section26["includeOvernightWrapForCityDepartureGap"]
        and minimum_wrap_gap > section26["maximumCityDepartureGapMinutes"]
    ):
        policy_conflicts.append(
            _finding(
                "overnight-wrap",
                "The literal cyclic city departure-gap ceiling is incompatible with the permitted departure window",
                shortestPossibleOvernightGap=minimum_wrap_gap,
                cityDepartureGapCeiling=section26[
                    "maximumCityDepartureGapMinutes"
                ],
                earliestDeparture=windows["earliestMinute"],
                latestDeparture=windows["hubOrFocusLatestMinute"],
            )
        )
    checks.append(
        _check(
            "section_26_service_gap_policy_consistency",
            "Section 2.6 service-gap policy consistency",
            "§2.5 / §2.6 Check B",
            "warning",
            policy_conflicts,
            "The cyclic city departure-gap rule is compatible with the operating window",
        )
    )

    numbering_findings = []
    route_blocks = {"CRJ200": 1, "CRJ700": 3, "CRJ900": 5, "MAX9": 7}
    for leg in legs:
        expected_hundred = route_blocks.get(leg["fleet"])
        if expected_hundred is not None and leg["route"] // 100 != expected_hundred:
            numbering_findings.append(
                _finding(
                    f"route-{leg['route']}",
                    f"Route {leg['route']} is outside the {leg['fleet']} number block",
                    route=leg["route"],
                    fleet=leg["fleet"],
                )
            )
        if not 1001 <= leg["flight"] <= 9999:
            numbering_findings.append(
                _finding(
                    f"flight-{leg['flight']}",
                    f"Flight number {leg['flight']} is not a four-digit number starting at 1001",
                    flight=leg["flight"],
                )
            )
    unique_numbering = {finding["id"]: finding for finding in numbering_findings}
    checks.append(
        _check(
            "numbering_conventions",
            "Route and flight numbering conventions",
            "§2.8 / Lesson 33",
            "error",
            unique_numbering.values(),
            "Route blocks and flight-number ranges follow the standing convention",
        )
    )

    forced = {
        code: set(labels)
        for code, labels in canonical["gatePlan"].get("forcedStandSplits", {}).items()
    }
    touch_on_stand = []
    stand_overflow = []
    gate_conflicts = []
    one_minute_overflow = []
    for city in sorted((city for city in cities if city["active"]), key=lambda city: city["sourceOrder"]):
        gate_count, stand_count = _capacity(city)
        claims = build_claims(legs, city["code"])
        if city["code"] in forced:
            claims = apply_forced_stand_splits(claims, forced[city["code"]])
        assignments, stand_middles = assign_gates(claims, gate_count, return_provenance=True)
        max_stand = max((slot - gate_count for _, slot in assignments if slot > gate_count), default=0)
        if max_stand > stand_count:
            stand_overflow.append(
                _finding(
                    city["code"],
                    f"{city['code']} needs stand {max_stand} but has {stand_count} configured stands",
                    city=city["code"],
                    requiredStands=max_stand,
                    configuredStands=stand_count,
                )
            )
        for claim, slot in assignments:
            if (
                slot > gate_count
                and claim not in stand_middles
                and claim.end - claim.start <= policy["turns"]["holdThresholdMinutes"]
            ):
                touch_on_stand.append(
                    _finding(
                        f"{city['code']}-{claim.label}-{claim.start}-{claim.end}",
                        f"{city['code']} claim {claim.label} requires passenger handling on stand {slot - gate_count}",
                        city=city["code"],
                        label=claim.label,
                        kind=claim.kind,
                        start=claim.start,
                        end=claim.end,
                        stand=slot - gate_count,
                    )
                )
        by_slot: defaultdict[int, list[GateClaim]] = defaultdict(list)
        for claim, slot in assignments:
            by_slot[slot].append(claim)
        for slot, slot_claims in by_slot.items():
            for index, first in enumerate(slot_claims):
                for second in slot_claims[index + 1 :]:
                    if overlaps(first, second):
                        gate_conflicts.append(
                            _finding(
                                f"{city['code']}-{slot}-{first.label}-{second.label}",
                                f"{city['code']} physical slot {slot} is double-booked",
                                city=city["code"],
                                slot=slot,
                                labels=[first.label, second.label],
                            )
                        )
        combined_capacity = gate_count + stand_count
        peak = 0
        peak_minute = 0
        for minute in range(1440):
            usage = sum(
                1
                for claim in claims
                if overlaps(claim, GateClaim(minute, minute + 1, "", "", "", None, None))
            )
            if usage > peak:
                peak, peak_minute = usage, minute
        if peak > combined_capacity:
            one_minute_overflow.append(
                _finding(
                    city["code"],
                    f"{city['code']} peaks at {peak} aircraft against combined capacity {combined_capacity}",
                    city=city["code"],
                    peak=peak,
                    peakMinute=peak_minute,
                    combinedCapacity=combined_capacity,
                )
            )
    checks.append(
        _check(
            "gate_assignment_conflicts",
            "Physical gate/stand double-booking",
            "§1.7 / §2.2",
            "error",
            gate_conflicts,
            "No assigned physical slot is double-booked cyclically",
        )
    )
    checks.append(
        _check(
            "passenger_touch_on_stand",
            "Passenger handling on stands",
            "§1.7 hard-stop addition",
            "error",
            touch_on_stand,
            "Every deplaning and boarding touch is assigned to a gate",
        )
    )
    checks.append(
        _check(
            "stand_capacity",
            "Configured hard-stand capacity",
            "§2.2",
            "error",
            stand_overflow,
            "Every assignment fits within configured stand capacity",
        )
    )
    checks.append(
        _check(
            "combined_capacity_peak",
            "One-minute combined capacity",
            "§1.7 / §2.2",
            "error",
            one_minute_overflow,
            "Every city's one-minute peak fits combined gate and stand capacity",
        )
    )

    runway_known = {city["code"] for city in cities if city["runwayLengthFeet"] is not None}
    if not runway_known:
        checks.append(
            _not_evaluated(
                "runway_screening",
                "Fleet/runway screening",
                "§2.12",
                "No active city has runway length populated in the pinned city snapshot",
                ["cities[].runwayLengthFeet"],
            )
        )
    else:
        runway_findings = []
        fleets_by_city: defaultdict[str, set[str]] = defaultdict(set)
        for leg in legs:
            fleets_by_city[leg["origin"]].add(leg["fleet"])
            fleets_by_city[leg["destination"]].add(leg["fleet"])
        for code in sorted(runway_known):
            length = city_by_code[code]["runwayLengthFeet"]
            for fleet in sorted(fleets_by_city[code]):
                threshold = policy["runwayScreeningFeet"][fleet]
                if length < threshold:
                    runway_findings.append(
                        _finding(
                            f"{code}-{fleet}",
                            f"{code}'s {length}-ft runway is below the {fleet} screening threshold",
                            city=code,
                            fleet=fleet,
                            runwayLengthFeet=length,
                            screeningThresholdFeet=threshold,
                        )
                    )
        checks.append(
            _check(
                "runway_screening",
                "Fleet/runway screening",
                "§2.12",
                "warning",
                runway_findings,
                "All populated runway lengths clear their fleets' screening thresholds",
                metrics={"citiesWithRunwayData": len(runway_known), "activeCities": len(active)},
            )
        )

    percentile_ready = all(
        "demandPercentile" in city for city in cities if city["active"] and city["role"] != "hub"
    )
    if not percentile_ready:
        checks.append(
            _not_evaluated(
                "tiered_service_minimums",
                "Percentile-tier service minimums",
                "§2.3",
                "Demand percentiles were not preserved in the v2.2.5 workbook or city snapshot",
                ["cities[].demandPercentile"],
            )
        )
    else:
        tier_findings = _validate_tiered_service(cities, legs, hubs, focus_cities)
        checks.append(
            _check(
                "tiered_service_minimums",
                "Percentile-tier service minimums",
                "§2.3",
                "error",
                tier_findings,
                "Every destination satisfies its tier minimum and hub-count cap",
            )
        )

    banks = canonical.get("hubBanks")
    bank_assignments = canonical.get("bankAssignments")
    if banks is None or bank_assignments is None:
        checks.append(
            _not_evaluated(
                "hub_bank_alignment",
                "Hub-bank count and alignment",
                "§1.6a",
                "The legacy workbook does not record bank definitions or per-leg bank assignments",
                ["hubBanks", "bankAssignments"],
            )
        )
    else:
        bank_findings = _validate_hub_banks(canonical, policy)
        checks.append(
            _check(
                "hub_bank_alignment",
                "Hub-bank count and alignment",
                "§1.6a",
                "error",
                bank_findings,
                "Hub-bank counts, widths, and assigned touches are valid",
            )
        )

    checks, unused_overrides = _apply_overrides(
        checks, policy, canonical["schedule"]["number"]
    )
    unused_override_check = _check(
        "unused_overrides",
        "Override integrity",
        "§1.11",
        "warning",
        (
            _finding(
                f"{override['checkId']}:{override['findingId']}",
                "Configured override did not match a current finding or has expired",
                override=override,
            )
            for override in unused_overrides
        ),
        "Every configured override matches a current finding",
    )
    checks.append(unused_override_check)

    status_counts = Counter(check["status"] for check in checks)
    effective_errors = sum(
        check["metrics"].get("effectiveFindingCount", len(check["findings"]))
        for check in checks
        if check["severity"] == "error" and check["status"] == "fail"
    )
    effective_warnings = sum(
        check["metrics"].get("effectiveFindingCount", len(check["findings"]))
        for check in checks
        if check["severity"] == "warning" and check["status"] == "warning"
    )
    overall = "fail" if effective_errors else ("review" if effective_warnings or status_counts["not_evaluated"] else "pass")
    return {
        "scheduleId": canonical["schedule"]["id"],
        "policyId": policy["id"],
        "status": overall,
        "summary": {
            "checks": len(checks),
            "passed": status_counts["pass"],
            "failed": status_counts["fail"],
            "warnings": status_counts["warning"],
            "notEvaluated": status_counts["not_evaluated"],
            "overridden": status_counts["overridden"],
            "effectiveErrorFindings": effective_errors,
            "effectiveWarningFindings": effective_warnings,
        },
        "checks": checks,
    }


def _validate_tiered_service(
    cities: list[dict[str, Any]],
    legs: list[dict[str, Any]],
    hubs: set[str],
    focus_cities: set[str],
) -> list[dict[str, Any]]:
    findings = []
    touches = Counter(code for leg in legs for code in (leg["origin"], leg["destination"]))
    directed = Counter((leg["origin"], leg["destination"]) for leg in legs)
    for city in cities:
        if not city["active"] or city["role"] == "hub":
            continue
        percentile = city["demandPercentile"]
        if percentile <= 25:
            minimum, cap = 3, 1
        elif percentile <= 70:
            minimum, cap = 6, 2
        elif percentile < 90:
            minimum, cap = 8, 3
        else:
            minimum, cap = 8, 4
        connected = {
            endpoint
            for leg in legs
            for endpoint in hubs | focus_cities
            if {leg["origin"], leg["destination"]} == {city["code"], endpoint}
        }
        hub_touches = sum(
            count
            for (origin, destination), count in directed.items()
            if city["code"] in (origin, destination)
            and (origin in hubs | focus_cities or destination in hubs | focus_cities)
        )
        if hub_touches < minimum or len(connected) > cap:
            findings.append(
                _finding(
                    city["code"],
                    f"{city['code']} does not satisfy its percentile-tier service envelope",
                    city=city["code"],
                    percentile=percentile,
                    totalFlights=touches[city["code"]],
                    hubOrFocusFlights=hub_touches,
                    minimumFlights=minimum,
                    connectedHubs=sorted(connected),
                    hubCountCap=cap,
                )
            )
        secondary_hubs = city["hubAssignments"][1:cap] if percentile >= 71 else []
        for secondary in secondary_hubs:
            if directed[(city["code"], secondary)] < 1 or directed[(secondary, city["code"])] < 1:
                findings.append(
                    _finding(
                        f"{city['code']}-{secondary}",
                        f"{city['code']} lacks a complete round trip to qualified secondary hub {secondary}",
                        city=city["code"],
                        hub=secondary,
                        outbound=directed[(city["code"], secondary)],
                        inbound=directed[(secondary, city["code"])],
                    )
                )
    return findings


def _validate_hub_banks(
    canonical: dict[str, Any], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    findings = []
    banks = {bank["id"]: bank for bank in canonical["hubBanks"]}
    legs = {leg["id"]: leg for leg in canonical["legs"]}
    counts = Counter(bank["hub"] for bank in banks.values())
    for hub, expected in policy["hubBankCounts"].items():
        if counts[hub] != expected:
            findings.append(
                _finding(
                    f"{hub}-count",
                    f"{hub} defines {counts[hub]} banks; policy calls for {expected}",
                    hub=hub,
                    actual=counts[hub],
                    expected=expected,
                )
            )
    for bank in banks.values():
        width = (bank["endMinute"] - bank["startMinute"]) % 1440
        if width > policy["hubBankWindowMinutes"]:
            findings.append(
                _finding(
                    f"{bank['id']}-width",
                    f"Bank {bank['id']} is {width} minutes wide",
                    bank=bank["id"],
                    width=width,
                    maximum=policy["hubBankWindowMinutes"],
                )
            )
    actual_assignments: Counter[tuple[str, str]] = Counter()
    for assignment in canonical["bankAssignments"]:
        actual_assignments[(assignment["legId"], assignment["operation"])] += 1
        bank = banks.get(assignment["bankId"])
        leg = legs.get(assignment["legId"])
        if bank is None or leg is None:
            findings.append(
                _finding(
                    f"{assignment['legId']}-{assignment['bankId']}",
                    "Bank assignment references a missing leg or bank",
                    assignment=assignment,
                )
            )
            continue
        touched_hub = (
            leg["destination"]
            if assignment["operation"] == "arrival"
            else leg["origin"]
        )
        if touched_hub != bank["hub"]:
            findings.append(
                _finding(
                    f"{assignment['legId']}-{assignment['operation']}-hub",
                    f"Bank {bank['id']} is at {bank['hub']} but the assigned touch is at {touched_hub}",
                    assignment=assignment,
                    bankHub=bank["hub"],
                    touchedHub=touched_hub,
                )
            )
        minute = (
            leg["arrivalMinute"] if assignment["operation"] == "arrival" else leg["departureMinute"]
        ) % 1440
        probe = GateClaim(minute, minute + 0.001, "", "", "", None, None)
        window = GateClaim(bank["startMinute"], bank["endMinute"], "", "", "", None, None)
        if not overlaps(probe, window):
            findings.append(
                _finding(
                    f"{assignment['legId']}-{assignment['operation']}",
                    f"{assignment['operation'].title()} for {assignment['legId']} falls outside bank {bank['id']}",
                    assignment=assignment,
                    minute=minute,
                    bankWindow=[bank["startMinute"], bank["endMinute"]],
                )
            )
    hubs = set(policy["hubs"])
    expected_assignments = {
        (leg["id"], operation)
        for leg in legs.values()
        for operation in ("arrival", "departure")
        if (operation == "arrival" and leg["destination"] in hubs)
        or (operation == "departure" and leg["origin"] in hubs)
    }
    for leg_id, operation in sorted(expected_assignments):
        count = actual_assignments[(leg_id, operation)]
        if count != 1:
            findings.append(
                _finding(
                    f"{leg_id}-{operation}-assignment-count",
                    f"{leg_id} {operation} has {count} bank assignments; exactly one is required",
                    legId=leg_id,
                    operation=operation,
                    assignments=count,
                )
            )
    return findings
