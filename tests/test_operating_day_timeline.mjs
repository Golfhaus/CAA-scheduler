import assert from "node:assert/strict";
import test from "node:test";
import {buildOperatingDayGrid} from "../web/operating-day-timeline.mjs";

test("operating day shows every hour with compact clocks and preserves midnight identity", () => {
  const grid = buildOperatingDayGrid(180, 1620);
  assert.deepEqual(grid.ticks.map((tick) => tick.label), [
    "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14",
    "15", "16", "17", "18", "19", "20", "21", "22", "23", "00", "01", "02",
  ]);
  assert.equal(grid.ticks.at(-1).minute, 1560);
  assert.equal(grid.ticks.at(-1).day, 1);
  grid.ticks.forEach((tick, i) => {
    assert.ok(Math.abs(tick.left - (grid.bands[i].left + grid.bands[i].width / 2)) < 1e-10);
  });
  assert.equal(grid.bands.length, 24);
  assert.equal(grid.hours, 24);
  assert.ok(grid.bands.every((band, i) => !i || band.shaded !== grid.bands[i - 1].shaded));
  assert.ok(Math.abs(grid.bands.reduce((total, band) => total + band.width, 0) - 100) < 1e-10);
});

test("extended route days keep hourly spacing through midnight", () => {
  const grid = buildOperatingDayGrid(120, 1740);
  assert.equal(grid.hours, 27);
  assert.equal(grid.ticks.length, 27);
  assert.equal(grid.ticks.at(-1).label, "04");
  assert.equal(grid.ticks.at(-1).day, 1);
  assert.equal(grid.bands.length, 27);
});

test("partial-hour labels stay centered in their visible bands", () => {
  const grid = buildOperatingDayGrid(-30, 90);
  assert.deepEqual(grid.ticks.map(({label, left}) => ({label, left})), [
    {label: "23", left: 12.5}, {label: "00", left: 50}, {label: "01", left: 87.5},
  ]);
  assert.deepEqual(grid.bands.map(({left, width}) => ({left, width})), [
    {left: 0, width: 25}, {left: 25, width: 50}, {left: 75, width: 25},
  ]);
});
