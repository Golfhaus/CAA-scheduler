import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { bankBreakdownAirports, buildHubBankBreakdown } from "../web/hub-bank-breakdown.mjs";

import {
  buildItineraries,
  buildDepartureHubMatrix,
  buildExtensionOpportunities,
  buildGateBankGuide,
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
  isRedEyeFlight,
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

const manifest = JSON.parse(await readFile(new URL("../web/schedules.json", import.meta.url), "utf8"));
const latest = manifest.schedules.find((entry) => entry.id === manifest.defaultScheduleId);
const load = async (key) => JSON.parse(await readFile(new URL(`../${latest.files[key]}`, import.meta.url), "utf8"));
const canonical = await load("canonical");
const operatingReport = await load("operatingValidation");
const gates = await load("gates");
const frequencyFleetPlan = {markets: [
  {origin: "DAY", destination: "JAX", allocations: [{fleet: "CRJ700", roundTrips: 1, legCount: 2}, {fleet: "MAX9", roundTrips: 3, legCount: 6}]},
  {origin: "JAX", destination: "SFB", allocations: [{fleet: "MAX9", roundTrips: 1, legCount: 2}]},
]};
const hubBankPlan = {hubs: [...new Set(canonical.hubBanks.map((bank) => bank.hub))].map((hub) => ({
  hub, banks: canonical.hubBanks.filter((bank) => bank.hub === hub),
}))};
// Small engine fixtures exercise rare tow and PHOS states absent from the released schedule.
function towPieces(label, start, end) {
  const base = {label, fleet: "CRJ700", kind: "ron", arrivalCity: "ROC", departureCity: "PGD"};
  return [
    {...base, start, end: start + 45, rowType: "gate", row: 11, moveTo: {rowType: "stand", row: 2}},
    {...base, start: start + 45, end: end - 60, rowType: "stand", row: 2},
    {...base, start: end - 60, end, rowType: "gate", row: 6, moveFrom: {rowType: "stand", row: 2}},
  ];
}

test("overview metrics reflect the frozen schedule", () => {
  assert.deepEqual(scheduleMetrics(canonical), {
    flights: 1128,
    cities: 105,
    routes: 181,
    lines: 20,
    markets: 552,
  });
  assert.deepEqual(fleetUsage(canonical), {
    CRJ200: 76,
    CRJ700: 54,
    CRJ900: 28,
    MAX9: 23,
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
  const leg = canonical.legs.find((item) => item.flight === 2087);
  assert.equal(legMatches(leg, "DAY"), true);
  assert.equal(legMatches(leg, "2087"), true);
  assert.equal(legMatches(leg, "703", "MAX9"), true);
  assert.equal(legMatches(leg, "flight:2087"), true);
  assert.equal(legMatches(leg, "route:2087"), false);
  assert.equal(legMatches(leg, "703", "CRJ200"), false);
  assert.equal(legMatches(leg, "", {line: "A", origin: "DAY", destination: "JAX"}), true);
  assert.equal(legMatches(leg, "", {line: "B"}), false);
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
  const opportunities = buildExtensionOpportunities(canonical, gates);
  assert.equal(opportunities.originators.length, 181);
  assert.equal(opportunities.terminators.length, 181);
  assert.ok(opportunities.originators.every((leg, index, values) => (
    index === 0 || values[index - 1].departureMinute >= leg.departureMinute
  )));
  const redEyes = opportunities.terminators.map((leg) => isRedEyeFlight(leg, canonical.operatingPolicy.departureWindows));
  assert.ok(redEyes.includes(true));
  assert.ok(redEyes.every((redEye, index) => index === 0 || Number(redEyes[index - 1]) <= Number(redEye)));
  assert.ok(opportunities.holds.length > 0);
  assert.ok(opportunities.holds.every((hold) => hold.duration >= 120));
  assert.ok(opportunities.holds.every((hold) => ["TURN", "ROD"].includes(hold.kind)));
  assert.ok(opportunities.holds.every((hold) => !String(hold.route).includes("->")));
  assert.ok(opportunities.holds.every((hold, index, values) => (
    index === 0 || values[index - 1].duration >= hold.duration
  )));
  assert.equal(formatDuration(761), "12h 41m");
});

test("bank breakdown conserves every hub touch and groups flights by the opposite endpoint", () => {
  assert.deepEqual(bankBreakdownAirports(canonical).map((city) => city.code), ["DAY", "JAX", "MCI", "PHF", "SYR", "BHM"]);
  for (const hub of canonical.operatingPolicy.hubs) {
    const breakdown = buildHubBankBreakdown(canonical, hub);
    assert.equal(breakdown.inbound, canonical.legs.filter((leg) => leg.destination === hub).length);
    assert.equal(breakdown.outbound, canonical.legs.filter((leg) => leg.origin === hub).length);
    assert.equal(breakdown.unassigned.inbound.length + breakdown.unassigned.outbound.length, 0);
    for (const bank of breakdown.banks) {
      assert.equal(bank.groups.reduce((total, group) => total + group.inbound.length, 0), bank.inbound.length);
      assert.equal(bank.groups.reduce((total, group) => total + group.outbound.length, 0), bank.outbound.length);
      for (const flight of [...bank.inbound, ...bank.outbound]) {
        assert.equal(flight.group, canonical.cities.find((city) => city.code === flight.city).group);
      }
    }
  }
  const phf = buildHubBankBreakdown(canonical, "PHF");
  assert.ok(phf.banks.some((bank) => bank.outsideWindow > 0));
  const bhm = buildHubBankBreakdown(canonical, "BHM");
  assert.equal(bhm.banks.length, 0);
  assert.equal(bhm.unassigned.inbound.length + bhm.unassigned.outbound.length, 94);
});

test("bank breakdown preserves explicit assignments without inferring missing banks or duplicating hub-to-hub flights", () => {
  const legs = [
    {id: "out", flight: 1, origin: "DAY", destination: "JAX", departureMinute: 290, arrivalMinute: 400},
    {id: "in", flight: 2, origin: "ALB", destination: "DAY", departureMinute: 280, arrivalMinute: 330},
    {id: "missing", flight: 3, origin: "DAY", destination: "ALB", departureMinute: 320, arrivalMinute: 420},
    {id: "unknown", flight: 4, origin: "XXX", destination: "DAY", departureMinute: 280, arrivalMinute: 350},
    {id: "wrap", flight: 5, origin: "ALB", destination: "DAY", departureMinute: 1300, arrivalMinute: 20},
  ];
  const fixture = {operatingPolicy: {hubs: ["DAY", "JAX"], focusCities: []}, cities: [
    {code: "DAY", group: "HUB"}, {code: "JAX", group: "HUB"}, {code: "ALB", group: "NEC"},
  ], legs, hubBanks: [
    {id: "DAY-B1", hub: "DAY", startMinute: 300, endMinute: 360},
    {id: "DAY-B2", hub: "DAY", startMinute: 1380, endMinute: 60},
    {id: "JAX-B1", hub: "JAX", startMinute: 380, endMinute: 440},
  ], bankAssignments: [
    {legId: "out", operation: "departure", bankId: "DAY-B1"},
    {legId: "out", operation: "departure", bankId: "DAY-B1"},
    {legId: "out", operation: "arrival", bankId: "JAX-B1"},
    {legId: "in", operation: "arrival", bankId: "DAY-B1"},
    {legId: "unknown", operation: "arrival", bankId: "obsolete"},
    {legId: "wrap", operation: "arrival", bankId: "DAY-B2"},
  ]};
  const result = buildHubBankBreakdown(fixture, "DAY");
  assert.equal(result.banks[0].outbound.length, 1);
  assert.equal(result.banks[0].outbound[0].group, "HUB");
  assert.equal(result.banks[0].outbound[0].outsideWindow, true);
  assert.equal(result.banks[0].inbound[0].group, "NEC");
  assert.equal(result.banks[1].inbound[0].outsideWindow, false);
  assert.equal(result.unassigned.outbound[0].id, "missing");
  assert.equal(result.unassigned.inbound[0].group, "Unknown");
  assert.equal(result.inbound, 3);
  assert.equal(result.outbound, 2);
  assert.equal(buildHubBankBreakdown(fixture, "JAX").banks[0].inbound.length, 1);
});

test("terminators keep red-eyes last and after-midnight arrivals late in the operating day", () => {
  const legs = [
    {route: "1", flight: "1", sequenceWithinRoute: 1, departureMinute: 60, arrivalMinute: 278},
    {route: "2", flight: "2", sequenceWithinRoute: 1, departureMinute: 270, arrivalMinute: 360},
    {route: "3", flight: "3", sequenceWithinRoute: 1, departureMinute: 1100, arrivalMinute: 1200},
    {route: "4", flight: "4", sequenceWithinRoute: 1, departureMinute: 1375, arrivalMinute: 1491},
    {route: "5", flight: "5", sequenceWithinRoute: 1, departureMinute: 1375, arrivalMinute: 51},
  ];
  const result = buildExtensionOpportunities({...canonical, legs}, {cities: []});
  assert.deepEqual(result.terminators.map((leg) => leg.route), ["2", "3", "4", "5", "1"]);
});

test("short successor RONs are excluded while same-route overnight turns and daytime RODs remain", () => {
  const claims = [
    {rowType: "gate", row: 1, kind: "turn", label: "321 -> 322", start: 1450, end: 1600},
    {rowType: "gate", row: 2, kind: "turn", label: "310", start: 1410, end: 1560},
    {rowType: "gate", row: 3, kind: "ron", label: "701", start: 600, end: 1000},
  ];
  const result = buildExtensionOpportunities({...canonical, legs: []}, {cities: [{code: "DAY", claims}]});
  assert.deepEqual(result.holds.map((hold) => [hold.route, hold.kind]), [["701", "ROD"], ["310", "TURN"]]);
});

test("bank guides deduplicate shared edges and map overnight banks into the gate operating day", () => {
  const hubBanks = [
    {hub: "DAY", id: "DAY-B1", startMinute: 300, endMinute: 360},
    {hub: "DAY", id: "DAY-B2", startMinute: 360, endMinute: 420},
    {hub: "DAY", id: "DAY-B3", startMinute: 1380, endMinute: 1500},
    {hub: "DAY", id: "DAY-B4", startMinute: 120, endMinute: 240},
    {hub: "JAX", id: "JAX-B1", startMinute: 300, endMinute: 360},
  ];
  const guide = buildGateBankGuide({hubBanks}, {code: "DAY", isHub: true});
  assert.deepEqual(guide.boundaries, [0, 60, 120, 180, 240, 1200, 1320, 1380, 1440]);
  assert.deepEqual(guide.labels.filter((bank) => bank.label === "B3").map(({start, duration}) => ({start, duration})), [{start: 1200, duration: 120}]);
  assert.deepEqual(guide.labels.filter((bank) => bank.label === "B4").map(({start, duration}) => ({start, duration})), [{start: 0, duration: 60}, {start: 1380, duration: 60}]);
  assert.deepEqual(buildGateBankGuide({hubBanks}, {code: "DAY"}), {boundaries: [], labels: []});
  assert.deepEqual(buildGateBankGuide({hubBanks}, {code: "DAY", isFocusCity: true}), guide);
  assert.deepEqual(buildGateBankGuide(canonical, {code: "BHM", isFocusCity: true}), {boundaries: [], labels: []});
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
  assert.equal(rows.length, 3);
  assert.equal(rows.reduce((total, row) => total + row.legCount, 0), 10);
  assert.equal(rows.some((row) => row.origin === "DAY" && row.destination === "JAX"), true);
  assert.equal(rows.every((row) => row.fleet && row.roundTrips > 0), true);
});

test("hub-bank windows flatten the latest schedule's configured banks", () => {
  const rows = flattenBankWindows(hubBankPlan);
  assert.equal(rows.length, canonical.hubBanks.length);
  assert.deepEqual(new Set(rows.map((row) => row.hub)), new Set(canonical.hubBanks.map((bank) => bank.hub)));
  assert.ok(rows.every((row) => row.endMinute > row.startMinute));
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
  const pieces = towPieces("701", 500, 900);
  const group = gateClaimGroup(pieces, pieces[1]);
  assert.equal(gateClaimDisplayKind(group), "ROD");
  assert.equal(gateClaimPath(group), "Gate 11 -> Stand 2 -> Gate 6");
  assert.deepEqual(group.map((claim) => gateClaimDisplayLabel(claim, group)), ["701", "701", "701"]);
  assert.equal(new Set(group.map((claim) => gateClaimGroupKey(gateClaimGroup(pieces, claim)))).size, 1);
});

test("overnight tow labels reserve route arrows for the 03:00 boundary blocks", () => {
  const pieces = towPieces("101 -> 102", 1200, 1740);
  const group = gateClaimGroup(pieces, pieces[0]);
  assert.equal(gateClaimDisplayKind(group), "RON");
  assert.deepEqual(group.map((claim) => gateClaimDisplayLabel(claim, group)), ["101", "101 -> 102", "102"]);
});

test("gate-stand-gate details describe only the selected segment", () => {
  const pieces = towPieces("101 -> 102", 851, 1717);
  const group = gateClaimGroup(pieces, pieces[0]);
  assert.deepEqual(gateClaimDetail(pieces[0], group, "PHF"), {
    start: 851, end: 896, position: "Gate 11", movement: "ROC -> PHF -> Stand 2",
  });
  assert.deepEqual(gateClaimDetail(pieces[1], group, "PHF"), {
    start: 896, end: 1657, position: "Stand 2", movement: "Gate 11 -> Stand 2 -> Gate 6",
  });
  assert.deepEqual(gateClaimDetail(pieces[2], group, "PHF"), {
    start: 1657, end: 1717, position: "Gate 6", movement: "Stand 2 -> PHF -> PGD",
  });
});

test("gate and stand cards report latest usage within fixed capacities", () => {
  for (const city of gates.cities) {
    assert.ok(maximumConcurrentPositionUsage(city.claims, "gate") <= city.nGates);
    assert.ok(maximumConcurrentPositionUsage(city.claims, "stand") <= city.nStands);
  }
});

test("the latest release has no passenger handling on stands", () => {
  assert.equal(operatingReport.checks.find((item) => item.id === "passenger_touch_on_stand").findings.length, 0);
  assert.deepEqual(passengerStandFindings(operatingReport, "JAX"), []);
});

test("only passenger-handling edges of a stand RON are highlighted", () => {
  const base = {rowType: "stand", label: "101 -> 102", kind: "ron"};
  const arrival = {...base, start: 1396, end: 1441};
  const overnight = {...base, start: 1441, end: 1680};
  const departure = {...base, start: 1680, end: 1740};
  const report = {checks: [{id: "passenger_touch_on_stand", findings: [arrival, departure].map((claim) => ({evidence: {city: "ALB", ...claim}}))}]};
  const findings = passengerStandFindings(report, "ALB");
  assert.equal(claimMatchesPassengerStandFinding("ALB", arrival, findings), true);
  assert.equal(claimMatchesPassengerStandFinding("ALB", overnight, findings), false);
  assert.equal(claimMatchesPassengerStandFinding("ALB", departure, findings), true);
});
