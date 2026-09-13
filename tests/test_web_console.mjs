import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  extractReferences,
  fleetUsage,
  formatMinute,
  legMatches,
  scheduleMetrics,
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
