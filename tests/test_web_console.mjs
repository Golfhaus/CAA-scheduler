import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildItineraries,
  extractReferences,
  fleetUsage,
  formatMinute,
  legMatches,
  paginate,
  passengerStandFindings,
  scheduleMetrics,
  selectItineraries,
  sortFlightsByDeparture,
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

test("published flights default to departure-time order", () => {
  const flights = [
    { flight: 3, dep: "12:00" },
    { flight: 2, dep: "04:30" },
    { flight: 1, dep: "04:30" },
  ];
  assert.deepEqual(sortFlightsByDeparture(flights).map((flight) => flight.flight), [1, 2, 3]);
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
    { start: 1380, duration: 60 },
    { start: 0, duration: 60 },
  ]);
  assert.equal(formatMinute(1500), "1:00 AM");
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
