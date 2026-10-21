import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import {buildItineraries} from "../web/app.mjs";
import {parseAirportDemand, buildServiceAnalysis, coverageView, screenTimingChange, compareServiceAnalyses, buildBankEffectiveness, sharedHubsMatch} from "../web/opportunity-analysis.mjs";
const manifest = JSON.parse(await readFile(new URL("../web/schedules.json", import.meta.url), "utf8"));
const latest = manifest.schedules.find((entry) => entry.id === manifest.defaultScheduleId);
const canonical = JSON.parse(await readFile(new URL(`../${latest.files.canonical}`, import.meta.url), "utf8"));
const demand = parseAirportDemand(await readFile(new URL("../data/reference/airport_od_matrix_consolidated_v2.csv", import.meta.url), "utf8"));
const baseline = buildServiceAnalysis(canonical, demand, buildItineraries);
const v131Canonical = JSON.parse(await readFile(new URL("../data/schedules/schedule_7_v1_3_1/canonical_schedule.json", import.meta.url), "utf8"));
const v131FrozenAudit = buildServiceAnalysis(v131Canonical, demand, buildItineraries);
const v141Canonical = JSON.parse(await readFile(new URL("../data/schedules/schedule_7_v1_4_1/canonical_schedule.json", import.meta.url), "utf8"));
const v141FrozenAudit = buildServiceAnalysis(v141Canonical, demand, buildItineraries);
test("shared hub filtering matches any checked hub and treats None as no shared hubs", () => {
  assert.equal(sharedHubsMatch(["JAX", "PHF"], new Set(["JAX"])), true);
  assert.equal(sharedHubsMatch(["MCI"], new Set(["JAX", "MCI"])), true);
  assert.equal(sharedHubsMatch(["SYR"], new Set(["JAX", "MCI"])), false);
  assert.equal(sharedHubsMatch([], new Set(["none"])), true);
  assert.equal(sharedHubsMatch(["PHF"], new Set(["none"])), false);
  assert.equal(sharedHubsMatch([], new Set(["JAX"])), false);
  assert.equal(sharedHubsMatch([], new Set(["none", "JAX"])), true);
  assert.equal(sharedHubsMatch(["JAX"], new Set(["none", "JAX"])), true);
  assert.equal(sharedHubsMatch([], new Set()), false);
  assert.equal(sharedHubsMatch(["JAX"], new Set()), false);
  const all = new Set([...baseline.hubs, "none"]);
  assert.ok(baseline.pairs.every((p) => sharedHubsMatch(p.forward.sharedHubs, all)));
});

const retime = (flight, shift) => {
  const candidate = structuredClone(canonical), screen = screenTimingChange(candidate, flight, shift), leg = candidate.legs.find((l) => l.flight === flight);
  leg.departureMinute += shift; leg.arrivalMinute += shift; leg.departure = screen.departure; leg.arrival = screen.arrival;
  return candidate;
};

test("directional coverage and pair gaps reproduce the independently audited current network", () => {
  const baseline = v131FrozenAudit;
  assert.equal(baseline.records.size, 10920);
  assert.equal([...baseline.records.values()].filter((r) => coverageView(r).gap).length, 5097);
  const counts = baseline.pairs.map((p) => Number(coverageView(p.forward).gap) + Number(coverageView(p.reverse).gap));
  assert.equal(counts.filter((n) => n === 2).length, 2133);
  assert.equal(counts.filter((n) => n === 1).length, 831);
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
    assert.equal(v141FrozenAudit.nearMisses.some((r) => r.market === market), false);
    assert.equal(coverageView(v141FrozenAudit.records.get(market)).stops, 1);
  }
  const hou = v141FrozenAudit.nearMisses.find((r) => r.market === "BLV-HOU");
  assert.equal(hou.adjustment, 6); assert.equal(hou.preferred.flight, 1357); assert.equal(hou.preferred.shift, 6);
  assert.match(hou.options[0].screen.issues.join(" "), /34 min/);
});

test("preview finds gains and slower-one-stop distinction without mutating the original schedule", () => {
  const original = JSON.stringify(v141Canonical);
  const candidate = structuredClone(v141Canonical); const changed = candidate.legs.find((l) => l.flight === 1357); changed.departureMinute += 6; changed.arrivalMinute += 6; changed.departure = "10:31"; changed.arrival = "11:35";
  const after = buildServiceAnalysis(candidate, demand, buildItineraries);
  const impact = compareServiceAnalyses(v141FrozenAudit, after);
  assert.equal(impact.lostPaths, 0); assert.deepEqual(impact.lost, []); assert.deepEqual(impact.slower, []);
  assert.ok(impact.gained.some((r) => r.market === "BLV-HOU"));
  const mke = v141FrozenAudit.records.get("MKE-SFB");
  assert.equal(mke.best[1].totalMinutes, 477); assert.equal(mke.best[2].totalMinutes, 310);
  assert.equal(JSON.stringify(v141Canonical), original);
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


test("v1.3.1 closes northeast Florida and DSM priority gaps with suitable geography", () => {
  for(const ne of ["HPN","HVN","ISP","BTV","ORH"]) for(const fl of ["PGD","DAB","FLL","PIE","SFB","SRQ"]) for(const [a,b]of[[ne,fl],[fl,ne]]){
    const v=coverageView(v131FrozenAudit.records.get(`${a}-${b}`),true);assert.ok(v.stops!=null&&v.stops<=1,`${a}-${b}`);
  }
  for(const market of ["RDU-DSM","DSM-RDU","JAX-DSM","PHF-DSM","DSM-PHF","SYR-DSM"])assert.equal(coverageView(v131FrozenAudit.records.get(market),true).stops,1,market);
  assert.equal(v131FrozenAudit.records.get("JAX-DSM").reasonableBest[1].totalMinutes,240);
  assert.equal(v131FrozenAudit.records.get("RDU-DSM").reasonableBest[1].totalMinutes,235);
});

test("RFD priority service works both ways and retains the ROA detour distinction", () => {
  for(const city of ["MYR","EYW","ECP","ILM","ROA","TLH"])for(const market of [`${city}-RFD`,`RFD-${city}`]){
    assert.equal(coverageView(baseline.records.get(market)).stops,1,market);
    if(city!=="ROA")assert.equal(coverageView(baseline.records.get(market),true).stops,1,market);
  }
  assert.equal(baseline.records.get("ROA-RFD").reasonableCounts[1],0);
});
