import {buildServiceAnalysis, coverageView, parseAirportDemand, compareServiceAnalyses, buildBankEffectiveness, sharedHubsMatch} from "./opportunity-analysis.mjs?v=20261017-shared-hubs";

const escape = (s) => String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const number = (n) => n == null ? "Unavailable" : Number(n).toLocaleString(undefined, {maximumFractionDigits: 1});
const $ = (id) => document.getElementById(id);
const button = (text, attrs) => `<button type="button" class="analysis-link" ${attrs}>${escape(text)}</button>`;
const market = (a, b, text = `${a} → ${b}`) => button(text, `data-analysis-origin="${escape(a)}" data-analysis-destination="${escape(b)}"`);
const route = (n) => button(`Route ${n}`, `data-analysis-route="${escape(n)}"`);
const label = (v) => v.stops == null ? "Unavailable within 2 connections" : v.stops === 0 ? "Nonstop" : `${v.stops} connection${v.stops === 1 ? "" : "s"}`;

export function createOpportunityUI({getCanonical, getManifest, enumerate, openMarket, openRoute, openGate, duration}) {
  let analysis = null, pending = null, generation = 0, active = "", coveragePage = 1, nearPage = 1, nearRows = [], matrixCells = [], selectedMiss = null, impactGeneration = 0;
  const geographic = () => $(active === "service-coverage" ? "coverage-geography" : "near-geography")?.value === "reasonable";
  const matching = (pair, query) => !query || `${pair.a} ${pair.b} ${analysis.cities.get(pair.a)?.name} ${analysis.cities.get(pair.b)?.name}`.toLowerCase().includes(query);
  const bestText = (v) => v.fastest ? duration(v.fastest.totalMinutes) : "—";
  const hint = (record, geo) => {
    const v = coverageView(record, geo);
    if (!v.gap) { const one = v.best[1], two = v.best[2]; return one && two && one.totalMinutes > two.totalMinutes ? "One-stop is slower than two-stop" : "Covered"; }
    if (geo && record.counts[1]) return "One-stop options take excessive detours";
    return record.sharedHubs.length ? `Timing at ${record.sharedHubs.join(", ")}` : "No shared connecting hub";
  };
  const paging = (id, type, count, page) => {
    const pages = Math.max(1, Math.ceil(count / 50));
    $(id).innerHTML = `<span>${count ? `${(page - 1) * 50 + 1}–${Math.min(page * 50, count)}` : "0"} of ${count.toLocaleString()}</span><div>${button("Previous", `data-analysis-page="${type}" data-analysis-page-value="${page - 1}" ${page <= 1 ? "disabled" : ""}`)}${button("Next", `data-analysis-page="${type}" data-analysis-page-value="${page + 1}" ${page >= pages ? "disabled" : ""}`)}</div>`;
  };
  async function ensure() {
    if (analysis) return analysis;
    if (pending) return pending;
    const token = generation, canonical = getCanonical();
    pending = (async () => {
      let demand = null, note = "";
      try {
        const pin = getManifest().buildSetup?.demandData;
        const schedulePin = canonical.provenance?.construction?.demandData?.id;
        if (schedulePin && schedulePin !== pin?.version) throw new Error("This schedule uses a different demand snapshot.");
        const r = await fetch(pin.manifest, {cache: "no-store"}); if (!r.ok) throw new Error("Demand manifest unavailable.");
        const manifest = await r.json(); if (manifest.id !== pin.version) throw new Error("Demand version differs from its manifest.");
        const csv = await fetch(manifest.sources.airportOdMatrix.filename, {cache: "no-store"}); if (!csv.ok) throw new Error("Demand matrix unavailable.");
        const text = await csv.text();
        if (globalThis.crypto?.subtle) {
          const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)))].map((b) => b.toString(16).padStart(2, "0")).join("");
          if (hash !== manifest.sources.airportOdMatrix.sha256) throw new Error("Demand matrix fingerprint differs from the pinned source.");
        }
        demand = parseAirportDemand(text);
        note = "Demand is pinned average daily O-D passengers, not forecast CAA loads. Missing demand is shown as unavailable.";
      } catch (error) { note = `Demand ranking unavailable: ${error.message} Coverage and timing remain available.`; }
      await new Promise((resolve) => setTimeout(resolve, 0));
      const result = buildServiceAnalysis(canonical, demand, enumerate);
      if (token !== generation || canonical !== getCanonical()) return null;
      analysis = result;
      for (const id of ["coverage-demand-note", "near-demand-note", "effectiveness-demand-note"]) $(id).textContent = note;
      populateBanks(); populateCoverageHubs(); return analysis;
    })().catch((error) => { if (token === generation) { pending = null; $("analysis-status").textContent = `Analysis unavailable: ${error.message}`; } return null; });
    return pending;
  }
  function populateCoverageHubs() {
    $("coverage-hub-options").innerHTML = [...analysis.hubs].sort().concat("none")
      .map((hub) => `<label class="coverage-hub-option"><input type="checkbox" value="${escape(hub)}" checked><span>${hub === "none" ? "None" : escape(hub)}</span></label>`).join("");
    $("coverage-shared-hubs").disabled = false;
  }
  function updateCoverageHubs() {
    if (analysis) { coveragePage = 1; renderCoverage(); }
  }
  function renderCoverage() {
    const geo = $("coverage-geography").value === "reasonable", query = $("coverage-search").value.trim().toLowerCase(), filter = $("coverage-gap").value, threshold = Math.max(0, Number($("coverage-demand").value) || 0);
    let both = 0, single = 0;
    const selectedHubs = new Set([...$("coverage-hub-options").querySelectorAll("input:checked")].map((input) => input.value));
    const pairs = analysis.pairs.map((p) => {
      const a = coverageView(p.forward, geo), b = coverageView(p.reverse, geo), count = Number(a.gap) + Number(b.gap);
      if (count === 2) both++; if (count === 1) single++;
      const demands = [p.forward.demand, p.reverse.demand];
      const demand = demands.every((n) => n != null) ? demands.reduce((s, n, i) => s + ((filter === "all" || [a, b][i].gap) ? n : 0), 0) : null;
      return {...p, aView: a, bView: b, count, demand};
    }).filter((p) => matching(p, query) && sharedHubsMatch(p.forward.sharedHubs, selectedHubs) && (filter === "all" || filter === "both" && p.count === 2 || filter === "one" && p.count === 1 || filter === "any" && p.count > 0) && (p.demand == null || p.demand >= threshold));
    pairs.sort((a, b) => (b.demand ?? -1) - (a.demand ?? -1) || a.key.localeCompare(b.key));
    coveragePage = Math.min(coveragePage, Math.max(1, Math.ceil(pairs.length / 50)));
    $("coverage-summary").textContent = `${both.toLocaleString()} pairs missing both ways · ${single.toLocaleString()} missing one way across the full schedule. Ranking counts demand only in missing directions; All pairs counts both directions.`;
    $("coverage-rows").innerHTML = pairs.slice((coveragePage - 1) * 50, coveragePage * 50).map((p) => `<tr><th>${escape(p.a)}–${escape(p.b)}<small>${escape(analysis.cities.get(p.a)?.name)} / ${escape(analysis.cities.get(p.b)?.name)}</small></th><td>${number(p.demand)}</td><td>${market(p.a, p.b)}<small>${label(p.aView)} · ${bestText(p.aView)}</small><small>${escape(hint(p.forward, geo))}</small></td><td>${market(p.b, p.a)}<small>${label(p.bView)} · ${bestText(p.bView)}</small><small>${escape(hint(p.reverse, geo))}</small></td><td>${p.forward.sharedHubs.length ? escape(p.forward.sharedHubs.join(", ")) : "None"}</td></tr>`).join("") || '<tr><td colspan="5">No city pairs match these filters.</td></tr>';
    paging("coverage-pagination", "coverage", pairs.length, coveragePage);
  }
  function renderNear() {
    const query = $("near-search").value.trim().toLowerCase(), hub = $("near-hub").value, maximum = Number($("near-limit").value), threshold = Math.max(0, Number($("near-demand").value) || 0), geo = $("near-geography").value === "reasonable";
    nearRows = analysis.nearMisses.filter((r) => (geo || r.gapCurrent) && r.adjustment <= maximum && (!hub || r.hub === hub) && (r.demand == null || r.demand >= threshold) && (!query || `${r.origin} ${r.destination} ${analysis.cities.get(r.origin)?.name} ${analysis.cities.get(r.destination)?.name}`.toLowerCase().includes(query)));
    if ($("near-sort").value === "change") nearRows.sort((a, b) => a.adjustment - b.adjustment || (b.demand ?? -1) - (a.demand ?? -1));
    nearPage = Math.min(nearPage, Math.max(1, Math.ceil(nearRows.length / 50)));
    $("near-summary").textContent = `${nearRows.length.toLocaleString()} missing directions within ${maximum} minutes. Changes are timing screens; gates, complete spacing and maintenance still need full validation.`;
    $("near-rows").innerHTML = nearRows.slice((nearPage - 1) * 50, nearPage * 50).map((r, i) => `<tr><th>${market(r.origin, r.destination)}</th><td>${number(r.demand)}</td><td>${escape(r.hub)}</td><td>${escape(r.first.flight)} arrives ${escape(r.first.arrival)}<small>${route(r.first.route)}</small></td><td>${escape(r.second.flight)} leaves ${escape(r.second.departure)}<small>${route(r.second.route)}</small></td><td>${duration(r.transfer)}<small>${r.adjustment} min adjustment</small></td><td>${r.preferred.shift > 0 ? "Delay" : "Advance"} ${r.preferred.flight} ${r.adjustment} min<small>${r.preferred.screen.issues.length ? "Needs coordinated changes" : "Turn, bank and window screens pass"}</small>${button("Preview impact", `data-analysis-miss="${(nearPage - 1) * 50 + i}"`)}</td></tr>`).join("") || '<tr><td colspan="7">No near-misses match these filters.</td></tr>';
    paging("near-pagination", "near", nearRows.length, nearPage);
  }
  async function previewMiss(index) {
    selectedMiss = nearRows[index]; if (!selectedMiss) return;
    $("near-preview").hidden = false;
    $("near-preview-title").textContent = `${selectedMiss.origin} → ${selectedMiss.destination} via ${selectedMiss.hub}`;
    $("near-change").innerHTML = selectedMiss.options.map((o, i) => `<option value="${i}" ${o === selectedMiss.preferred ? "selected" : ""}>${o.shift > 0 ? "Delay" : "Advance"} flight ${o.flight} ${Math.abs(o.shift)} minutes</option>`).join("");
    $("near-preview-title").focus(); await renderImpact();
  }
  async function renderImpact() {
    if (!selectedMiss) return;
    const token = ++impactGeneration, version = generation, original = analysis, selected = selectedMiss, geo = $("near-geography").value === "reasonable";
    const option = selected.options[Number($("near-change").value)];
    $("near-impact").textContent = "Comparing service across the network…";
    $("near-constraints").innerHTML = `<p>Flight ${option.flight}: ${escape(option.screen.leg.departure)}–${escape(option.screen.leg.arrival)} becomes <strong>${option.screen.departure}–${option.screen.arrival}</strong>, local airport times.</p><p>${option.screen.turns.map((t) => `${escape(t.side)}: ${t.minutes} min`).join(" · ")}</p><p>${option.screen.issues.length ? option.screen.issues.map(escape).join("; ") : "Turn, assigned-bank, operating-window and spacing-floor screens pass."} Full gate, spacing and maintenance validation is still required.</p>`;
    await new Promise((resolve) => setTimeout(resolve, 0));
    try {
      const candidate = structuredClone(original.canonical); const leg = candidate.legs.find((l) => l.flight === option.flight);
      leg.departureMinute += option.shift; leg.arrivalMinute += option.shift; leg.departure = option.screen.departure; leg.arrival = option.screen.arrival;
      const demand = Object.fromEntries([...original.cities.keys()].map((a) => [a, Object.fromEntries([...original.records.values()].filter((r) => r.origin === a).map((r) => [r.destination, r.demand]))]));
      const after = buildServiceAnalysis(candidate, demand, enumerate), impact = compareServiceAnalyses(original, after, geo);
      if (token !== impactGeneration || version !== generation) return;
      const target = coverageView(after.records.get(selected.market), geo), before = coverageView(original.records.get(selected.market), geo);
      const one = target.best[1];
      $("near-impact").innerHTML = `<p><strong>${impact.gained.length} one-stop/direct markets gained · ${impact.lost.length} lost · ${impact.lostPaths} itinerary choices lost</strong></p><p>Fastest journeys: ${impact.faster.length} improved, ${impact.slower.length} slower. Target: ${bestText(before)} → ${bestText(target)}${one ? `; new one-stop trip ${duration(one.totalMinutes)}` : ""}.${one && before.fastest && one.totalMinutes > before.fastest.totalMinutes ? " The one-stop trip is slower than the current fastest option." : ""}</p>${[ ["Coverage gained", impact.gained], ["One-stop/direct coverage lost", impact.lost], ["Slower fastest journeys", impact.slower] ].map(([title, rows]) => `<details ${title !== "Coverage gained" && rows.length ? "open" : ""}><summary>${title}: ${rows.length}</summary>${rows.length ? `<ul>${rows.map((r) => `<li>${market(r.origin, r.destination)} · ${number(r.demand)} O-D/day${title.includes("Slower") ? ` · ${duration(r.beforeMinutes)} → ${duration(r.afterMinutes)}` : ""}</li>`).join("")}</ul>` : "<p>None.</p>"}</details>`).join("")}<p class="stats-note">Preview only. The selected schedule and its gate assignments are unchanged.</p>`;
    } catch (error) { if (token === impactGeneration) $("near-impact").textContent = `Preview unavailable: ${error.message}`; }
  }
  function populateBanks() {
    const hubs = [...analysis.hubs].sort();
    for (const id of ["near-hub", "effectiveness-hub"]) {
      const old = $(id).value; $(id).innerHTML = (id === "near-hub" ? '<option value="">All hubs / focus cities</option>' : "") + hubs.map((h) => `<option value="${h}">${h} · ${escape(analysis.cities.get(h)?.name)}</option>`).join("");
      $(id).value = hubs.includes(old) ? old : id === "near-hub" ? "" : hubs.includes("MCI") ? "MCI" : hubs[0];
    }
    populateBankSelector();
  }
  function populateBankSelector() {
    const hub = $("effectiveness-hub").value, old = $("effectiveness-bank").value;
    const banks = (analysis.canonical.hubBanks || []).filter((b) => b.hub === hub);
    $("effectiveness-bank").innerHTML = '<option value="all">Whole day</option>' + banks.map((b) => `<option value="${escape(b.id)}">${escape(b.id)} · ${String(Math.floor(b.startMinute / 60)).padStart(2, "0")}:${String(b.startMinute % 60).padStart(2, "0")}</option>`).join("") + '<option value="unassigned">Unassigned flights</option>';
    $("effectiveness-bank").value = banks.some((b) => b.id === old) || ["all", "unassigned"].includes(old) ? old : "all";
  }
  function renderEffectiveness() {
    const result = buildBankEffectiveness(analysis, $("effectiveness-hub").value, $("effectiveness-bank").value);
    $("effectiveness-summary").textContent = `${result.arrivals.length} arrivals · ${result.departures.length} departures · ${result.markets.length} unique directional markets · ${number(result.uniqueDemand)} underlying O-D/day. Demand is counted once per market, not once per flight pairing.`;
    $("effectiveness-warning").textContent = `${result.inboundWithoutConnections} arrivals have no useful onward connection; ${result.outboundWithoutFeed} departures receive no useful inbound feed. Feed includes flights in other banks within ${analysis.minimum}–${analysis.maximum} minutes and the 2.25 distance limit.`;
    const flightRows = (rows, direction) => rows.map((r) => `<tr><td>${r.leg.flight}</td><td>${escape(direction === "in" ? r.leg.origin : r.leg.destination)}</td><td>${escape(direction === "in" ? r.leg.arrival : r.leg.departure)}</td><td>${new Set(r.choices.map((c) => direction === "in" ? c.second.destination : c.first.origin)).size}</td><td>${route(r.leg.route)}</td></tr>`).join("") || '<tr><td colspan="5">No flights in this selection.</td></tr>';
    $("effectiveness-inbound").innerHTML = flightRows(result.inbound, "in"); $("effectiveness-outbound").innerHTML = flightRows(result.outbound, "out");
    const matrix = $("effectiveness-matrix"); matrixCells = [];
    if (result.arrivals.length * result.departures.length > 1600) { matrix.innerHTML = '<p>Select an individual bank to inspect the transfer matrix. Whole-day feed counts above include every flight.</p>'; return; }
    matrix.innerHTML = `<div class="table-shell"><table class="transfer-matrix"><thead><tr><th>Arriving / departing</th>${result.departures.map((l) => `<th>${l.destination}<small>${l.flight} · ${l.departure}</small></th>`).join("")}</tr></thead><tbody>${result.matrix.map((cells, i) => `<tr><th>${result.arrivals[i].origin}<small>${result.arrivals[i].flight} · ${result.arrivals[i].arrival}</small></th>${cells.map((c) => { const index = matrixCells.push(c) - 1; return `<td><button type="button" class="transfer-cell ${c.connection ? "transfer-valid" : "transfer-invalid"}" data-transfer-cell="${index}" aria-label="${escape(`${c.first.origin} to ${c.second.destination}: ${c.connection ? "valid transfer" : c.reason}, ${c.transfer} minutes`)}">${c.transfer}<small>${c.connection ? "Works" : c.first.origin === c.second.destination ? "Return" : "Miss"}</small></button></td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  const root = $("view-sked-stats");
  root.addEventListener("click", (event) => {
    const m = event.target.closest("[data-analysis-origin]"); if (m) { openMarket(m.dataset.analysisOrigin, m.dataset.analysisDestination); return; }
    const r = event.target.closest("[data-analysis-route]"); if (r) { openRoute(r.dataset.analysisRoute); return; }
    const p = event.target.closest("[data-analysis-page]"); if (p && !p.disabled) { if (p.dataset.analysisPage === "coverage") { coveragePage = Number(p.dataset.analysisPageValue); renderCoverage(); } else { nearPage = Number(p.dataset.analysisPageValue); renderNear(); } return; }
    const miss = event.target.closest("[data-analysis-miss]"); if (miss) { void previewMiss(Number(miss.dataset.analysisMiss)); return; }
    const cell = event.target.closest("[data-transfer-cell]"); if (cell) {
      const c = matrixCells[Number(cell.dataset.transferCell)]; if (!c) return;
      $("effectiveness-detail").hidden = false;
      $("effectiveness-detail").innerHTML = `<h3 tabindex="-1">${escape(c.first.origin)} → ${escape(c.second.destination)} via ${escape(c.first.destination)}</h3><p>${c.first.flight} arrives ${escape(c.first.arrival)}; ${c.second.flight} departs ${escape(c.second.departure)} · ${c.transfer} min. ${c.connection ? "Valid timed and geographic transfer." : escape(c.reason) + "."}</p><p>${market(c.first.origin, c.second.destination, "Open travel options")} · ${route(c.first.route)} · ${route(c.second.route)} · ${button("Hub gates", `data-analysis-gate="${escape(c.first.destination)}"`)}</p>`;
      $("effectiveness-detail").querySelector("h3").focus(); return;
    }
    const gate = event.target.closest("[data-analysis-gate]"); if (gate) openGate(gate.dataset.analysisGate);
  });
  for (const id of ["coverage-search", "coverage-gap", "coverage-geography", "coverage-demand"]) $(id).addEventListener(id.includes("search") || id.includes("demand") ? "input" : "change", () => { if (analysis) { coveragePage = 1; renderCoverage(); } });
  $("coverage-hub-options").addEventListener("change", updateCoverageHubs);
  for (const [id, checked] of [["coverage-hubs-all", true], ["coverage-hubs-clear", false]]) {
    $(id).addEventListener("click", () => {
      $("coverage-hub-options").querySelectorAll("input").forEach((input) => { input.checked = checked; });
      updateCoverageHubs();
    });
  }
  for (const id of ["near-search", "near-hub", "near-limit", "near-geography", "near-demand", "near-sort"]) $(id).addEventListener(id.includes("search") || id.includes("demand") ? "input" : "change", () => { if (analysis) { nearPage = 1; renderNear(); $("near-preview").hidden = true; selectedMiss = null; impactGeneration++; } });
  $("near-change").addEventListener("change", () => { void renderImpact(); });
  $("effectiveness-hub").addEventListener("change", () => { if (analysis) { populateBankSelector(); renderEffectiveness(); $("effectiveness-detail").hidden = true; } });
  $("effectiveness-bank").addEventListener("change", () => { if (analysis) { renderEffectiveness(); $("effectiveness-detail").hidden = true; } });
  return {
    reset() {
      generation++; impactGeneration++; analysis = null; pending = null; coveragePage = nearPage = 1; selectedMiss = null; nearRows = []; matrixCells = [];
      $("coverage-shared-hubs").disabled = true;
      $("coverage-hub-options").textContent = "";
      for (const id of ["coverage-rows", "near-rows", "effectiveness-inbound", "effectiveness-outbound", "effectiveness-matrix", "coverage-summary", "near-summary", "effectiveness-summary"]) $(id).textContent = "";
      $("near-preview").hidden = true; $("effectiveness-detail").hidden = true;
    },
    async activate(tab) {
      active = tab;
      if (!["service-coverage", "connection-misses", "bank-effectiveness"].includes(tab)) { $("analysis-status").textContent = ""; return; }
      const token = generation; $("analysis-status").textContent = "Analyzing current schedule…";
      if (!await ensure() || token !== generation || active !== tab) return;
      $("analysis-status").textContent = "";
      if (tab === "service-coverage") renderCoverage(); else if (tab === "connection-misses") renderNear(); else renderEffectiveness();
    },
  };
}
