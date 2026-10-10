import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import {routingDetailOptions, buildRoutingDetails} from "../web/routing-details.mjs";

const manifest = JSON.parse(await readFile(new URL("../web/schedules.json", import.meta.url), "utf8"));
const entry = manifest.schedules.find((entry) => entry.id === manifest.defaultScheduleId);
const load = async (key) => JSON.parse(await readFile(new URL(`../${entry.files[key]}`, import.meta.url), "utf8"));
const canonical = await load("canonical");
const gates = await load("gates");

test("routing selector identifies every current route by number, day, line and fleet", () => {
  const options = routingDetailOptions(canonical);
  assert.equal(options.length, 181);
  assert.equal(new Set(options.map((option) => option.id)).size, options.length);
  assert.deepEqual(options.find((option) => option.id === "323"), {id: "323", route: 323, line: "AK", day: 3, fleet: "CRJ700"});
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
  assert.deepEqual([startGate.city, startGate.kind, startGate.row, startGate.start, startGate.end], ["CHS", "gate", 1, 180, 440]);
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
