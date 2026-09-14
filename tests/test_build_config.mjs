import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildConfigFilename,
  createBuildConfig,
  normalizeBuildConfig,
  serializeBuildConfig,
  validateBuildConfig,
} from "../web/build-config.mjs";

const canonical = JSON.parse(
  await readFile(
    new URL("../data/schedules/schedule_6_v2_2_5/canonical_schedule.json", import.meta.url),
    "utf8",
  ),
);
const manifest = JSON.parse(
  await readFile(new URL("../web/schedules.json", import.meta.url), "utf8"),
);

test("new setup is explicit and schedule-specific", () => {
  const config = createBuildConfig(canonical, manifest);
  assert.equal(config.schedule.number, 7);
  assert.equal(config.startingPoint.scheduleId, "schedule_6_v2_2_5");
  assert.deepEqual(config.fleetCounts, canonical.schedule.fleetCounts);
  canonical.schedule.fleetCounts.MAX9 = 999;
  assert.equal(config.fleetCounts.MAX9, 35);
  canonical.schedule.fleetCounts.MAX9 = 35;
  assert.equal(config.inputs.demandData.version, "");
});

test("preflight blocks an unpinned demand snapshot", () => {
  const config = createBuildConfig(canonical, manifest);
  const report = validateBuildConfig(config, canonical);
  assert.equal(report.status, "fail");
  assert.equal(report.checks.find((item) => item.id === "input_pins").status, "fail");

  config.inputs.demandData.version = "BTS DB1C 2026-09";
  const ready = validateBuildConfig(config, canonical);
  assert.equal(ready.status, "pass");
  assert.equal(ready.checks.find((item) => item.id === "curfew_enforcement").status, "pass");
});

test("preflight rejects invalid fleet counts and network changes", () => {
  const config = createBuildConfig(canonical, manifest);
  config.inputs.demandData.version = "BTS DB1C 2026-09";
  config.fleetCounts.CRJ200 = -1;
  config.networkChanges = [
    { airport: "JAX", action: "remove", targetStatus: "", notes: "" },
    { airport: "JAX", action: "status_change", targetStatus: "hub", notes: "" },
  ];
  const report = validateBuildConfig(config, canonical);
  assert.equal(report.status, "fail");
  assert.equal(report.checks.find((item) => item.id === "fleet_plan").status, "fail");
  assert.equal(report.checks.find((item) => item.id === "network_changes").status, "fail");
});

test("airport additions produce a runway-screening warning", () => {
  const config = createBuildConfig(canonical, manifest);
  config.inputs.demandData.version = "BTS DB1C 2026-09";
  config.networkChanges.push({
    airport: "ZZZ",
    action: "add",
    targetStatus: "destination",
    notes: "Candidate addition",
  });
  const report = validateBuildConfig(config, canonical);
  assert.equal(report.status, "pass");
  assert.equal(report.checks.find((item) => item.id === "airport_metadata").status, "warning");
});

test("export and import normalize to the same portable JSON", () => {
  const config = createBuildConfig(canonical, manifest);
  config.inputs.demandData.version = "BTS DB1C 2026-09";
  const serialized = serializeBuildConfig(config);
  const imported = normalizeBuildConfig(JSON.parse(serialized));
  assert.equal(serializeBuildConfig(imported), serialized);
  assert.equal(buildConfigFilename(imported), "schedule_7_v0_1_0_build_config.json");
});
