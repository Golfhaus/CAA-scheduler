import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import {routingDetailOptions, buildRoutingDetails, routeFlightUtilization,
  buildCriticalPeriodUtilization, formatFlightTime} from "../web/routing-details.mjs";

const manifest = JSON.parse(await readFile(new URL("../web/schedules.json", import.meta.url), "utf8"));
const entry = manifest.schedules.find((entry) => entry.id === manifest.defaultScheduleId);
const load = async (key) => JSON.parse(await readFile(new URL(`../${entry.files[key]}`, import.meta.url), "utf8"));
const canonical = await load("canonical");
const gates = await load("gates");

test("flight totals clip both operating-day and critical-period boundaries", () => {
  assert.deepEqual(routeFlightUtilization([
    {start: 150, end: 210}, {start: 330, end: 390},
    {start: 1290, end: 1350}, {start: 1590, end: 1650},
  ]), {totalFlightMinutes: 180, criticalFlightMinutes: 60,
    criticalGroundMinutes: 900, criticalUtilization: 1 / 16});
  assert.deepEqual(routeFlightUtilization([
    {start: 60, end: 180}, {start: 180, end: 360},
    {start: 1320, end: 1620}, {start: 1620, end: 1680},
  ]), {totalFlightMinutes: 480, criticalFlightMinutes: 0,
    criticalGroundMinutes: 960, criticalUtilization: 0});
  assert.equal(formatFlightTime(555), "9h15m");
  assert.equal(formatFlightTime(60), "1h00m");
  assert.equal(formatFlightTime(0), "0h00m");
});

test("utilization follows the origin clock across time zones and excludes flying after 22:00", () => {
  const makeLeg = (origin, destination, departureMinute, arrivalMinute, sequenceWithinRoute) => ({
    route: 1, line: "A", day: 1, fleet: "CRJ200", flight: sequenceWithinRoute,
    origin, destination, departureMinute, arrivalMinute, sequenceWithinRoute,
  });
  const fixture = {cities: [
    {code: "AAA", timezone: "Eastern"}, {code: "BBB", timezone: "Central"},
    {code: "CCC", timezone: "Mountain"},
  ], legs: [makeLeg("AAA", "BBB", 300, 360, 1),
    makeLeg("BBB", "CCC", 420, 480, 2), makeLeg("CCC", "AAA", 1200, 0, 3)]};
  const detail = buildRoutingDetails(fixture, null, 1);
  assert.equal(detail.totalFlightMinutes, 360);
  assert.equal(detail.criticalFlightMinutes, 180);
  assert.equal(detail.criticalGroundMinutes, 780);
  assert.equal(detail.zone, "ET");
});

test("critical utilization ranks every route ascending with numeric route tie-breaking", () => {
  const fixture = {cities: [{code: "AAA", timezone: "Eastern"}], legs: [10, 3, 2].map((route) => ({
    route, line: "A", day: route, fleet: "CRJ200", flight: route,
    origin: "AAA", destination: "AAA", sequenceWithinRoute: 1,
    departureMinute: route === 3 ? 300 : 400, arrivalMinute: route === 3 ? 350 : 460,
  }))};
  assert.deepEqual(buildCriticalPeriodUtilization(fixture).map((r) => r.route), [3, 2, 10]);
  const ranking = buildCriticalPeriodUtilization(canonical);
  assert.equal(ranking.length, routingDetailOptions(canonical).length);
  assert.equal(new Set(ranking.map((r) => r.route)).size, ranking.length);
  ranking.forEach((row, i) => {
    if (i) assert.ok(ranking[i - 1].criticalFlightMinutes <= row.criticalFlightMinutes);
    const detail = buildRoutingDetails(canonical, gates, row.route);
    assert.equal(row.criticalFlightMinutes, detail.criticalFlightMinutes);
    assert.equal(row.totalFlightMinutes, detail.totalFlightMinutes);
    assert.equal(row.criticalFlightMinutes + row.criticalGroundMinutes, 960);
    assert.ok(row.criticalFlightMinutes >= 0 && row.criticalFlightMinutes <= 960);
  });
});

test("routing selector identifies every current route by number, day, line and fleet", () => {
  const options = routingDetailOptions(canonical);
  assert.equal(options.length, new Set(canonical.legs.map((leg) => leg.route)).size);
  assert.equal(new Set(options.map((option) => option.id)).size, options.length);
  assert.deepEqual(options.find((option) => option.id === "323"), {id: "323", route: 323, line: "AK", day: entry.id === "schedule_7_v1_3_3" ? 6 : entry.id === "schedule_7_v1_3_2" ? 6 : 3, fleet: "CRJ700"});
  assert.ok(options.every((option, index) => !index || Number(options[index - 1].route) < Number(option.route)));
  assert.equal(buildRoutingDetails(canonical, gates, "missing"), null);
});

test("flight geometry uses one time zone while tooltips retain local clocks and midnight", () => {
  const detail = buildRoutingDetails(canonical, gates, 337);
  assert.equal(detail.zone, "CT");
  const flight = detail.flights.find((block) => block.leg.flight === 2172);
  assert.deepEqual([flight.start, flight.end, flight.end - flight.start], [1224, 1381, 157]);
  assert.match(flight.title, /Flight 2172.*MCI → PHF/);
  assert.match(flight.detail, /20:24 CT.*00:01 ET \(\+1 day\)/);
  const late = buildRoutingDetails(canonical, gates, 308);
  const returnFlight = late.flights.find((block) => block.leg.flight === 2160);
  assert.deepEqual([returnFlight.start, returnFlight.end], [1425, 1558]);
  assert.match(returnFlight.detail, /22:45 CT.*01:58 ET \(\+1 day\)/);
  assert.equal(late.blockMinutes, 689);
});

test("ground blocks use actual positions and correctly align overnight handoffs without flight overlap", () => {
  const detail = buildRoutingDetails(canonical, gates, 308);
  const startGate = detail.blocks.find((block) => block.role === "originator");
  assert.deepEqual([startGate.city, startGate.kind, startGate.row, startGate.start, startGate.end], ["CHS", "gate", entry.id === "schedule_7_v1_3_3" ? 2 : 1, 180, 440]);
  const stand = detail.blocks.find((block) => block.kind === "stand");
  assert.deepEqual([stand.city, stand.row, stand.start, stand.end], ["CLT", 1, 1603, 1620]);
  assert.match(stand.title, /CLT.*Stand 1/);
  assert.match(stand.detail, /02:43 ET \(\+1 day\)–03:00 ET \(\+1 day\)/);
  for (const option of routingDetailOptions(canonical)) {
    const chart = buildRoutingDetails(canonical, gates, option.id);
    assert.equal(chart.flights.length, canonical.legs.filter((leg) => String(leg.route) === option.id).length);
    for (const block of chart.blocks) {
      assert.ok(block.start >= chart.start && block.end <= chart.end && block.end > block.start);
      if (block.kind === "inflight") continue;
      assert.ok(chart.flights.every((flight) => block.end <= flight.start || block.start >= flight.end), `Ground overlaps a flight on ${option.id}`);
      assert.ok(gates.cities.find((city) => city.code === block.city).claims.includes(block.claim));
      assert.ok(block.row >= 1);
    }
  }
});
