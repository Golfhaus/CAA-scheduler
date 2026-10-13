import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand, buildServiceAnalysis, coverageView, screenTimingChange, compareServiceAnalyses, buildBankEffectiveness} from "../web/opportunity-analysis.mjs";
const manifest = JSON.parse(await readFile(new URL("../web/schedules.json", import.meta.url), "utf8"));
const latest = manifest.schedules.find((entry) => entry.id === manifest.defaultScheduleId);
const canonical = JSON.parse(await readFile(new URL(`../${latest.files.canonical}`, import.meta.url), "utf8"));
const demand = parseAirportDemand(await readFile(new URL("../data/reference/airport_od_matrix_consolidated_v2.csv", import.meta.url), "utf8"));
const baseline = buildServiceAnalysis(canonical, demand, buildItineraries);
const retime = (flight, shift) => {
  const candidate = structuredClone(canonical), screen = screenTimingChange(candidate, flight, shift), leg = candidate.legs.find((l) => l.flight === flight);
  leg.departureMinute += shift; leg.arrivalMinute += shift; leg.departure = screen.departure; leg.arrival = screen.arrival;
  return candidate;
};

test("directional coverage and pair gaps reproduce the independently audited current network", () => {
  assert.equal(baseline.records.size, 10920);
  assert.equal([...baseline.records.values()].filter((r) => coverageView(r).gap).length, 5198);
  const counts = baseline.pairs.map((p) => Number(coverageView(p.forward).gap) + Number(coverageView(p.reverse).gap));
  assert.equal(counts.filter((n) => n === 2).length, 2174);
  assert.equal(counts.filter((n) => n === 1).length, 850);
  assert.equal(coverageView(baseline.records.get("BLV-SFB")).gap, false);
  assert.equal(coverageView(baseline.records.get("SFB-BLV")).stops, 1);
});

test("demand parser preserves directionality, zero, quoted metadata and missing-data failures", () => {
  assert.equal(demand.CAK.PGD, 103.6); assert.equal(demand.PGD.CAK, 109.7);
  const text = 'Title\n"note, with a quote ""here"""\nOrigin \\ Dest,A,B\nA,,0\nB,2.5,\n';
  assert.deepEqual(parseAirportDemand(text), {A: {A: 0, B: 0}, B: {A: 2.5, B: 0}});
  assert.throws(() => parseAirportDemand(text.replace('A,,0', 'A,,')), /Missing or invalid/);
  assert.throws(() => parseAirportDemand(text.replace('B,2.5,', 'B,-1,')), /Missing or invalid/);
  const missing = buildServiceAnalysis(canonical, null, buildItineraries);
  assert.equal(missing.records.get("CAK-PGD").demand, null);
});

test("completed repairs disappear from near-misses and remaining repairs retain aircraft screening", () => {
  for (const market of ["BLV-SFB", "MKE-SFB", "PGD-CAK", "DAL-PNS", "VPS-BWI", "RDU-SGF", "PIT-BHM"]) {
    assert.equal(baseline.nearMisses.some((r) => r.market === market), false);
    assert.equal(coverageView(baseline.records.get(market)).stops, 1);
  }
  const hou = baseline.nearMisses.find((r) => r.market === "BLV-HOU");
  assert.equal(hou.adjustment, 6); assert.equal(hou.preferred.flight, 1357); assert.equal(hou.preferred.shift, 6);
  assert.match(hou.options[0].screen.issues.join(" "), /34 min/);
});

test("preview finds gains and slower-one-stop distinction without mutating the original schedule", () => {
  const original = JSON.stringify(canonical);
  const after = buildServiceAnalysis(retime(1357, 6), demand, buildItineraries);
  const impact = compareServiceAnalyses(baseline, after);
  assert.equal(impact.lostPaths, 0); assert.deepEqual(impact.lost, []); assert.deepEqual(impact.slower, []);
  assert.ok(impact.gained.some((r) => r.market === "BLV-HOU"));
  const mke = baseline.records.get("MKE-SFB");
  assert.equal(mke.best[1].totalMinutes, 477); assert.equal(mke.best[2].totalMinutes, 310);
  assert.equal(JSON.stringify(canonical), original);
});

test("R307 DAY service creates useful one-stop coverage and preserves the fast Dallas journey", () => {
  for (const [market, minutes] of [["PIT-BHM",306],["MCI-PIT",217],["PIT-GRR",275],["PIT-DAL",231]]) {
    const r=baseline.records.get(market);
    assert.equal(coverageView(r).stops,1);
    assert.equal(r.best[1].totalMinutes,minutes);
    assert.ok(r.reasonableBest[1]);
  }
});

test("geographic coverage identifies app-listed detours instead of labeling them outright timetable gaps", () => {
  const row = baseline.records.get("DAL-MSY");
  assert.equal(coverageView(row).gap, false); assert.equal(coverageView(row, true).gap, true);
});

test("bank counts use unique O-D markets and include transfers across assigned bank boundaries", () => {
  const bank = buildBankEffectiveness(baseline, "MCI", "MCI-B1");
  assert.ok(bank.arrivals.length > 0 && bank.departures.length > 0);
  assert.equal(new Set(bank.markets.map((m) => m.key)).size, bank.markets.length);
  assert.ok(Math.abs(bank.uniqueDemand - bank.markets.reduce((s, m) => s + m.demand, 0)) < 1e-8);
  assert.ok(bank.inbound.some((r) => r.choices.some((choice) => !bank.departures.includes(choice.second))));
  const bhm = buildBankEffectiveness(baseline, "BHM", "unassigned");
  assert.ok(bhm.arrivals.length && bhm.departures.length);
});

test("midnight transfers and both connection-window boundaries are inclusive", () => {
  const c = structuredClone(canonical);
  c.cities = [{code:"AAA", active:true, timezone:"Eastern", latitude:0, longitude:0}, {code:"JAX", active:true, timezone:"Eastern", latitude:0, longitude:1}, {code:"BBB", active:true, timezone:"Eastern", latitude:0, longitude:2}];
  c.operatingPolicy.hubs = ["JAX"]; c.operatingPolicy.focusCities = []; c.hubBanks = []; c.bankAssignments = [];
  c.legs = [{id:"a",flight:1,origin:"AAA",destination:"JAX",departure:"22:50",arrival:"23:50",departureMinute:1370,arrivalMinute:1430,route:1,line:"A",day:1,sequenceWithinRoute:1,fleet:"MAX9"},{id:"b",flight:2,origin:"JAX",destination:"BBB",departure:"00:20",arrival:"01:20",departureMinute:20,arrivalMinute:80,route:2,line:"B",day:1,sequenceWithinRoute:1,fleet:"MAX9"}];
  assert.equal(coverageView(buildServiceAnalysis(c, null, buildItineraries).records.get("AAA-BBB")).stops, 1);
  c.legs[1].departure="03:50"; c.legs[1].arrival="04:50";c.legs[1].departureMinute=230;c.legs[1].arrivalMinute=290;
  assert.equal(coverageView(buildServiceAnalysis(c, null, buildItineraries).records.get("AAA-BBB")).stops, 1);
  c.legs[1].departure="03:51";c.legs[1].departureMinute=231;
  assert.equal(coverageView(buildServiceAnalysis(c, null, buildItineraries).records.get("AAA-BBB")).gap, true);
  assert.equal(buildServiceAnalysis(c,null,buildItineraries).nearMisses[0].adjustment,1);
});
