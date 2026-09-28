import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildItineraries,
  buildDepartureHubMatrix,
  buildExtensionOpportunities,
  claimMatchesPassengerStandFinding,
  departureHubTimetableFilters,
  extractReferences,
  flattenBankWindows,
  flattenFrequencyMarkets,
  fleetUsage,
  gateClaimDetail,
  gateClaimDisplayKind,
  gateClaimDisplayLabel,
  gateClaimGroup,
  gateClaimGroupKey,
  gateClaimPath,
  formatRemainingAircraft,
  formatDuration,
  formatMinute,
  formatMinute24,
  instructionId,
  instructionReferenceTokens,
  legMatches,
  marketMatches,
  maximumConcurrentPositionUsage,
  paginate,
  passengerStandFindings,
  routingEndpointKinds,
  scheduleMetrics,
  selectItineraries,
  sortFlightsByDeparture,
  sortRoutingsByRouteAndSequence,
  splitClaimSegments,
} from "../web/app.mjs";

const canonical = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/canonical_schedule.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const operatingReport = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/operating_validation_report.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const gates = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/gates.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const schedule7Gates = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_7_v1_1_1/gates.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const schedule713Canonical = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_7_v1_1_3/canonical_schedule.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const schedule713Gates = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_7_v1_1_3/gates.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const frequencyFleetPlan = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/frequency_fleet_plan.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const hubBankPlan = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/hub_bank_plan.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const aircraftRoutePlan = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/aircraft_route_plan.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const routingRepairPlan = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/routing_repair_plan.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const bankMaterializationDiagnostic = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/bank_materialization_diagnostic.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const exactMaterializationPlan = JSON.parse(
  await readFile(
    new URL(
      "../data/schedules/schedule_6_v2_2_5/exact_materialization_plan.json",
      import.meta.url,
    ),
    "utf8",
  ),
);

test("overview metrics reflect the frozen schedule", () => {
  assert.deepEqual(scheduleMetrics(canonical), {
    flights: 1383,
    cities: 105,
    routes: 225,
    lines: 20,
    markets: 634,
  });
  assert.deepEqual(fleetUsage(canonical), {
    CRJ200: 80,
    CRJ700: 65,
    CRJ900: 45,
    MAX9: 35,
  });
});

test("departure hub matrix counts flights and distinguishes hubs from focus cities", () => {
  const matrix = buildDepartureHubMatrix({
    cities: [
      { code: "AAA", name: "Alpha", isHub: false, isFocusCity: false },
      { code: "HUB", name: "Hub City", isHub: true, isFocusCity: false },
      { code: "FOC", name: "Focus City", isHub: false, isFocusCity: true },
    ],
    flights: [
      { origin: "AAA", dest: "HUB" },
      { origin: "AAA", dest: "HUB" },
      { origin: "AAA", dest: "FOC" },
      { origin: "HUB", dest: "AAA" },
    ],
  });
  assert.deepEqual(matrix.destinations.map((city) => city.code), ["HUB", "FOC"]);
  assert.deepEqual(matrix.rows.map((row) => row.city.code), ["AAA", "FOC", "HUB"]);
  assert.deepEqual(matrix.rows[0].counts, { HUB: 2, FOC: 1 });
  assert.deepEqual(matrix.rows[1].counts, { HUB: 0, FOC: 0 });
});

test("departure hub cells open a clean non-stop Timetable filter", () => {
  assert.deepEqual(departureHubTimetableFilters("AAA", "HUB"), {
    search: "",
    origin: "AAA",
    destination: "HUB",
    fleet: "",
    connections: "nonstop",
  });
});

test("routing search covers operational identifiers", () => {
  const leg = canonical.legs[0];
  assert.equal(legMatches(leg, "BWI"), true);
  assert.equal(legMatches(leg, "1001"), true);
  assert.equal(legMatches(leg, "101", "CRJ200"), true);
  assert.equal(legMatches(leg, "flight:1001"), true);
  assert.equal(legMatches(leg, "route:1001"), false);
  assert.equal(legMatches(leg, "101", "MAX9"), false);
  assert.equal(legMatches(leg, "", { line: "Q", origin: "BHM", destination: "BWI" }), true);
  assert.equal(legMatches(leg, "", { line: "A" }), false);
});

test("routing pagination supports requested row counts and all rows", () => {
  const values = Array.from({ length: 600 }, (_, index) => index);
  assert.equal(paginate(values, 2, 250).rows.length, 250);
  assert.equal(paginate(values, 1, 500).rows.length, 500);
  assert.deepEqual(paginate(values, 4, "all").rows, values);
});

test("routing endpoints distinguish originators and terminators", () => {
  const routeId = canonical.legs.find(
    (candidate) => canonical.legs.filter((leg) => leg.route === candidate.route).length >= 3,
  ).route;
  const route = canonical.legs
    .filter((leg) => leg.route === routeId)
    .sort((left, right) => left.sequenceWithinRoute - right.sequenceWithinRoute);
  const endpointKinds = routingEndpointKinds(canonical.legs);
  assert.equal(endpointKinds.get(route[0].flight), "routing-originator");
  assert.equal(endpointKinds.get(route.at(-1).flight), "routing-terminator");
  assert.equal(endpointKinds.get(route[1].flight), "");
});

test("extension opportunities sort endpoints and combine long physical holds", () => {
  const opportunities = buildExtensionOpportunities(schedule713Canonical, schedule713Gates);
  assert.equal(opportunities.originators.length, 179);
  assert.equal(opportunities.terminators.length, 179);
  assert.ok(opportunities.originators.every((leg, index, values) => (
    index === 0 || values[index - 1].departureMinute >= leg.departureMinute
  )));
  assert.ok(opportunities.terminators.every((leg, index, values) => (
    index === 0 || values[index - 1].arrivalMinute <= leg.arrivalMinute
  )));
  assert.ok(opportunities.holds.length > 0);
  assert.ok(opportunities.holds.every((hold) => hold.duration >= 120));
  assert.ok(opportunities.holds.every((hold) => ["TURN", "ROD"].includes(hold.kind)));
  assert.ok(opportunities.holds.every((hold, index, values) => (
    index === 0 || values[index - 1].duration >= hold.duration
  )));
  assert.equal(formatDuration(761), "12h 41m");
});

test("planning market filters preserve fleet and match either market endpoint", () => {
  const row = { fleet: "CRJ700", origin: "BHM", destination: "JAX", legs: 3 };
  assert.equal(marketMatches(row, { fleet: "CRJ700", origin: "BHM" }), true);
  assert.equal(marketMatches(row, { destination: "JAX" }), true);
  assert.equal(marketMatches(row, { fleet: "MAX9" }), false);
  assert.equal(marketMatches(row, { destination: "BHM" }), true);
  assert.equal(marketMatches(row, { origin: "BHM", destination: "JAX" }), true);
  assert.equal(marketMatches(row, { origin: "BHM", destination: "BHM" }), false);
});

test("fresh frequency markets flatten into filterable fleet rows", () => {
  const rows = flattenFrequencyMarkets(frequencyFleetPlan);
  assert.equal(rows.length, 370);
  assert.equal(rows.reduce((total, row) => total + row.legCount, 0), 1430);
  assert.equal(rows.some((row) => row.origin === "CHS" && row.destination === "PHF"), true);
  assert.equal(rows.every((row) => row.fleet && row.roundTrips > 0), true);
});

test("hub-bank windows flatten into the 24 policy-required rows", () => {
  const rows = flattenBankWindows(hubBankPlan);
  assert.equal(rows.length, 24);
  assert.deepEqual(new Set(rows.map((row) => row.hub)), new Set(["DAY", "JAX", "MCI", "PHF", "SYR"]));
  assert.equal(rows.every((row) => row.endMinute - row.startMinute === 60), true);
  assert.equal(rows.every((row) => row.arrivalCount > 0 && row.departureCount > 0), true);
});

test("aircraft route plan exposes the complete, curfew-safe feasibility result", () => {
  assert.equal(aircraftRoutePlan.summary.routedLegs, 1430);
  assert.equal(aircraftRoutePlan.summary.unplacedRoundTrips, 0);
  assert.equal(aircraftRoutePlan.summary.configuredAircraft, 225);
  assert.equal(aircraftRoutePlan.summary.requiredAircraft, 409);
  assert.equal(aircraftRoutePlan.summary.curfewViolations, 0);
});

test("routing repair fits the selected fleet while retaining materialization guard", () => {
  assert.equal(routingRepairPlan.status, "pass");
  assert.equal(routingRepairPlan.summary.routedLegs, 1430);
  assert.equal(routingRepairPlan.summary.configuredAircraft, 225);
  assert.equal(routingRepairPlan.summary.requiredAircraft, 209);
  assert.equal(routingRepairPlan.summary.aircraftShortfall, 0);
  assert.equal(routingRepairPlan.summary.curfewViolations, 0);
  assert.equal(routingRepairPlan.summary.destinationsWithoutRon, 0);
  assert.equal(routingRepairPlan.summary.rollingRonViolations, 0);
  assert.equal(routingRepairPlan.materializationStatus, "pending_bank_alignment");
});

test("bank-window lower bound fits each fleet before non-hub integration", () => {
  assert.equal(bankMaterializationDiagnostic.directionalBankAssignment, "independent");
  assert.equal(bankMaterializationDiagnostic.bankWindowTiming, "full_core_five_minute_options");
  assert.equal(bankMaterializationDiagnostic.status, "pending_nonhub_integration");
  assert.equal(bankMaterializationDiagnostic.summary.bankedLegs, 1190);
  assert.equal(bankMaterializationDiagnostic.summary.nonHubLegs, 240);
  assert.equal(bankMaterializationDiagnostic.summary.fleetAllocationShortfall, 0);
  assert.equal(bankMaterializationDiagnostic.fleetPlan.CRJ200.bankAndRonMinimumAircraft, 67);
  assert.equal(bankMaterializationDiagnostic.fleetPlan.CRJ200.configuredAircraft, 80);
});

test("exact materialization integrates every leg inside the selected fleet", () => {
  assert.equal(exactMaterializationPlan.status, "pass");
  assert.equal(exactMaterializationPlan.materializationStatus, "complete");
  assert.equal(exactMaterializationPlan.summary.routedLegs, 1430);
  assert.equal(exactMaterializationPlan.summary.bankAlignedLegs, 1190);
  assert.equal(exactMaterializationPlan.summary.nonHubIntegratedLegs, 240);
  assert.equal(exactMaterializationPlan.summary.requiredAircraft, 208);
  assert.equal(exactMaterializationPlan.summary.curfewViolations, 0);
  assert.equal(exactMaterializationPlan.summary.destinationsWithoutRon, 0);
  assert.equal(exactMaterializationPlan.summary.rollingRonViolations, 0);
});

test("exact fleet headroom is displayed as positive remaining aircraft", () => {
  assert.equal(formatRemainingAircraft({shortfall: 0, remainingAircraft: 7}), "7");
  assert.equal(formatRemainingAircraft({shortfall: 2, remainingAircraft: 0}), "Short 2");
});

test("published flights default to departure-time order", () => {
  const flights = [
    { flight: 3, dep: "12:00" },
    { flight: 2, dep: "04:30" },
    { flight: 1, dep: "04:30" },
  ];
  assert.deepEqual(sortFlightsByDeparture(flights).map((flight) => flight.flight), [1, 2, 3]);
});

test("routings default to route then sequence order", () => {
  const legs = [
    { route: 102, sequenceWithinRoute: 1, flight: 1004 },
    { route: 101, sequenceWithinRoute: 2, flight: 1002 },
    { route: 101, sequenceWithinRoute: 1, flight: 1003 },
    { route: 101, sequenceWithinRoute: 1, flight: 1001 },
  ];
  assert.deepEqual(
    sortRoutingsByRouteAndSequence(legs).map((leg) => leg.flight),
    [1001, 1003, 1002, 1004],
  );
});

test("connection search uses hubs, including the BHM override supplied by the console", () => {
  const timetable = {
    minConnect: 30,
    maxConnect: 240,
    flights: [
      { flight: 1, origin: "AAA", dest: "BHM", dep: "08:00", arr: "09:00", fleet: "CRJ200" },
      { flight: 2, origin: "BHM", dest: "BBB", dep: "09:30", arr: "10:30", fleet: "CRJ200" },
      { flight: 3, origin: "AAA", dest: "XXX", dep: "08:10", arr: "09:10", fleet: "CRJ200" },
      { flight: 4, origin: "XXX", dest: "BBB", dep: "09:40", arr: "10:40", fleet: "CRJ200" },
      { flight: 5, origin: "AAA", dest: "DAY", dep: "07:00", arr: "08:00", fleet: "CRJ200" },
      { flight: 6, origin: "DAY", dest: "MCI", dep: "08:30", arr: "09:30", fleet: "CRJ200" },
      { flight: 7, origin: "MCI", dest: "CCC", dep: "10:00", arr: "11:00", fleet: "CRJ200" },
    ],
  };
  const zones = Object.fromEntries(["AAA", "BHM", "BBB", "XXX", "DAY", "MCI", "CCC"].map((code) => [code, "Eastern"]));
  const itineraries = buildItineraries(timetable, "AAA", new Set(["BHM", "DAY", "MCI"]), zones);
  assert.equal(itineraries.some((item) => item.dest === "BBB" && item.stops === 1 && item.legs[0].dest === "BHM"), true);
  assert.equal(itineraries.some((item) => item.dest === "BBB" && item.stops === 1 && item.legs[0].dest === "XXX"), false);
  assert.equal(itineraries.some((item) => item.dest === "CCC" && item.stops === 2), true);
});

test("itinerary selection keeps every nonstop, caps one-stops at six, and only fills to six with two-stops", () => {
  const make = (dest, stops, index, totalMinutes) => ({
    dest,
    stops,
    totalMinutes,
    departureMinute: index,
    legs: [{ flight: `${dest}-${stops}-${index}` }],
  });
  const itineraries = [
    ...[1, 2].map((index) => make("BBB", 0, index, 60)),
    ...Array.from({ length: 8 }, (_, index) => make("BBB", 1, index + 10, 300 - index)),
    ...Array.from({ length: 3 }, (_, index) => make("BBB", 2, index + 20, 400 + index)),
    make("CCC", 0, 30, 60),
    ...Array.from({ length: 2 }, (_, index) => make("CCC", 1, index + 40, 180 + index)),
    ...Array.from({ length: 5 }, (_, index) => make("CCC", 2, index + 50, 240 + index)),
  ];
  const selected = selectItineraries(itineraries, "all");
  assert.equal(selected.filter((item) => item.dest === "BBB" && item.stops === 0).length, 2);
  assert.equal(selected.filter((item) => item.dest === "BBB" && item.stops === 1).length, 6);
  assert.equal(selected.filter((item) => item.dest === "BBB" && item.stops === 2).length, 0);
  assert.equal(selected.filter((item) => item.dest === "CCC").length, 6);
  assert.equal(selected.filter((item) => item.dest === "CCC" && item.stops === 2).length, 3);
  assert.equal(selectItineraries(itineraries, "max1").some((item) => item.stops === 2), false);
  assert.equal(selectItineraries(itineraries, "nonstop").every((item) => item.stops === 0), true);
});

test("validation evidence produces navigation references", () => {
  const references = extractReferences({
    city: "BHM",
    arrivalFlight: 1201,
    departureFlight: 1202,
    route: 501,
    line: "H",
    fleet: "CRJ900",
  });
  assert.deepEqual(references, {
    flights: [1201, 1202],
    routes: [501],
    lines: ["H"],
    cities: ["BHM"],
    fleets: ["CRJ900"],
  });
});

test("validation instruction references preserve sections, checks, additions, and lessons", () => {
  assert.deepEqual(instructionReferenceTokens("§2.5 / Lesson 32"), ["§2.5", "Lesson 32"]);
  assert.deepEqual(instructionReferenceTokens("§2.6 Check B"), ["§2.6 Check B"]);
  assert.deepEqual(instructionReferenceTokens("§1.7 hard-stop addition"), ["§1.7 hard-stop addition"]);
  assert.equal(instructionId("§1.6a"), "section-1-6a");
  assert.equal(instructionId("Lesson 31"), "lesson-31");
});

test("every blocking baseline finding has a console destination", () => {
  const unlinked = operatingReport.checks
    .filter((check) => check.status === "fail")
    .flatMap((check) => check.findings)
    .filter((finding) => {
      const references = extractReferences(finding.evidence);
      return !Object.values(references).some((values) => values.length);
    });
  assert.equal(unlinked.length, 0);
});

test("gate claims split cleanly across midnight", () => {
  assert.deepEqual(splitClaimSegments(1380, 1500), [
    { start: 0, duration: 60 },
    { start: 1380, duration: 60 },
  ]);
  assert.equal(formatMinute(1500), "1:00 AM");
});

test("gate claims map into the 03:00–03:00 operating window", () => {
  assert.deepEqual(splitClaimSegments(0, 60, 180), [
    { start: 1260, duration: 60 },
  ]);
  assert.deepEqual(splitClaimSegments(1680, 1740, 180), [
    { start: 60, duration: 60 },
  ]);
  assert.deepEqual(splitClaimSegments(1085, 1948, 180), [
    { start: 0, duration: 328 },
    { start: 905, duration: 535 },
  ]);
  assert.equal(formatMinute24(180), "03:00");
  assert.equal(formatMinute24(1380), "23:00");
  assert.equal(formatMinute24(1620), "03:00");
});

test("daytime stand holds are labeled ROD and expose the complete gate path", () => {
  const phf = schedule7Gates.cities.find((city) => city.code === "PHF");
  const selected = phf.claims.find((claim) => claim.label === "705" && claim.kind === "ron");
  const group = gateClaimGroup(phf.claims, selected);
  assert.equal(gateClaimDisplayKind(group), "ROD");
  assert.equal(gateClaimPath(group), "Gate 16 -> Stand 3 -> Gate 9");
  assert.deepEqual(group.map((claim) => gateClaimDisplayLabel(claim, group)), ["705", "705", "705"]);
  assert.equal(new Set(group.map((claim) => gateClaimGroupKey(gateClaimGroup(phf.claims, claim)))).size, 1);
});

test("overnight tow labels reserve route arrows for the 03:00 boundary blocks", () => {
  const phf = schedule7Gates.cities.find((city) => city.code === "PHF");
  const selected = phf.claims.find((claim) => claim.label === "715 -> 716");
  const group = gateClaimGroup(phf.claims, selected);
  assert.equal(gateClaimDisplayKind(group), "RON");
  assert.equal(gateClaimPath(group), "Gate 15 -> Stand 1 -> Gate 2");
  assert.deepEqual(
    group.map((claim) => gateClaimDisplayLabel(claim, group)),
    ["715", "715 -> 716", "716"],
  );

  const gateHold = phf.claims.find((claim) => claim.label === "337 -> 338");
  assert.equal(gateClaimDisplayLabel(gateHold, gateClaimGroup(phf.claims, gateHold)), "337 -> 338");
});

test("gate-stand-gate details describe only the selected segment", () => {
  const phf = schedule713Gates.cities.find((city) => city.code === "PHF");
  const pieces = phf.claims
    .filter((claim) => claim.label === "354 -> 352")
    .sort((a, b) => a.start - b.start);
  assert.equal(pieces.length, 3);
  const group = gateClaimGroup(phf.claims, pieces[0]);
  assert.deepEqual(gateClaimDetail(pieces[0], group, "PHF"), {
    start: 851,
    end: 896,
    position: "Gate 11",
    movement: "ROC -> PHF -> Stand 2",
  });
  assert.deepEqual(gateClaimDetail(pieces[1], group, "PHF"), {
    start: 896,
    end: 1657,
    position: "Stand 2",
    movement: "Gate 11 -> Stand 2 -> Gate 6",
  });
  assert.deepEqual(gateClaimDetail(pieces[2], group, "PHF"), {
    start: 1657,
    end: 1717,
    position: "Gate 6",
    movement: "Stand 2 -> PHF -> PGD",
  });
});

test("gate and stand cards report maximum concurrent usage", () => {
  const phf = schedule7Gates.cities.find((city) => city.code === "PHF");
  assert.equal(maximumConcurrentPositionUsage(phf.claims, "gate"), 16);
  assert.equal(maximumConcurrentPositionUsage(phf.claims, "stand"), 6);
});

test("stand passenger-handling counts come from the authoritative operating report", () => {
  const findings = passengerStandFindings(operatingReport, "JAX");
  assert.equal(findings.length, 1);
  assert.equal(findings[0].evidence.kind, "ron");
  assert.equal(
    operatingReport.checks.find((item) => item.id === "passenger_touch_on_stand").findings.length,
    35,
  );
});

test("only passenger-handling edges of a stand RON are highlighted", () => {
  const city = gates.cities.find((item) => item.code === "ALB");
  const claims = city.claims.filter((claim) => claim.rowType === "stand" && claim.label === "358 -> 359");
  const findings = passengerStandFindings(operatingReport, "ALB");
  const arrival = claims.find((claim) => claim.start === 1396 && claim.end === 1441);
  const overnight = claims.find((claim) => claim.start === 1441 && claim.end === 1680);
  const departure = claims.find((claim) => claim.start === 1680 && claim.end === 1740);
  assert.equal(claimMatchesPassengerStandFinding("ALB", arrival, findings), true);
  assert.equal(claimMatchesPassengerStandFinding("ALB", overnight, findings), false);
  assert.equal(claimMatchesPassengerStandFinding("ALB", departure, findings), true);
});
