import {
  buildConfigFilename,
  createBuildConfig,
  normalizeBuildConfig,
  serializeBuildConfig,
  validateBuildConfig,
} from "./build-config.mjs";

const DEFAULT_PAGE_SIZE = 50;
const GATE_WINDOW_START = 180;
const CONNECTIONS_HUB_OVERRIDE = new Set(["BHM"]);
const TIMEZONE_OFFSETS = { Eastern: -300, Central: -360, Mountain: -420 };

const state = {
  manifest: null,
  scheduleEntry: null,
  canonical: null,
  structural: null,
  operating: null,
  planning: null,
  planningValidation: null,
  demandPlan: null,
  frequencyFleetPlan: null,
  hubBankPlan: null,
  aircraftRoutePlan: null,
  routingRepairPlan: null,
  bankMaterializationDiagnostic: null,
  exactMaterializationPlan: null,
  timetable: null,
  gates: null,
  instructions: null,
  instructionId: "section-1-1",
  buildConfig: null,
  buildPreflight: null,
  routingPage: 1,
  planningPage: 1,
  routingPageSize: DEFAULT_PAGE_SIZE,
  timetablePage: 1,
  itineraryCache: new Map(),
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatMinute(value) {
  const normalized = ((Math.round(Number(value)) % 1440) + 1440) % 1440;
  const hours = Math.floor(normalized / 60);
  const minutes = normalized % 60;
  const suffix = hours >= 12 ? "PM" : "AM";
  const displayHour = hours % 12 || 12;
  return `${displayHour}:${String(minutes).padStart(2, "0")} ${suffix}`;
}

export function formatMinute24(value) {
  const normalized = ((Math.round(Number(value)) % 1440) + 1440) % 1440;
  const hours = Math.floor(normalized / 60);
  const minutes = normalized % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function toMinutes(value) {
  const [hours, minutes] = String(value).split(":").map(Number);
  return hours * 60 + minutes;
}

export function waitMinutes(arrival, departure) {
  return (toMinutes(departure) - toMinutes(arrival) + 1440) % 1440;
}

export function sortFlightsByDeparture(flights) {
  return [...flights].sort(
    (a, b) => toMinutes(a.dep) - toMinutes(b.dep) || Number(a.flight) - Number(b.flight)
  );
}

function flightDurationMinutes(flight, timezoneByCode) {
  const originOffset = TIMEZONE_OFFSETS[timezoneByCode[flight.origin]] ?? 0;
  const destinationOffset = TIMEZONE_OFFSETS[timezoneByCode[flight.dest]] ?? 0;
  const departureUtc = toMinutes(flight.dep) - originOffset;
  const arrivalUtc = toMinutes(flight.arr) - destinationOffset;
  return (arrivalUtc - departureUtc + 1440) % 1440;
}

function itineraryKey(legs) {
  return legs.map((leg) => leg.flight).join("-");
}

export function buildItineraries(timetable, origin, hubCodes, timezoneByCode = {}) {
  const flightsByOrigin = new Map();
  timetable.flights.forEach((flight) => {
    if (!flightsByOrigin.has(flight.origin)) flightsByOrigin.set(flight.origin, []);
    flightsByOrigin.get(flight.origin).push(flight);
  });
  const minConnect = timetable.minConnect ?? 30;
  const maxConnect = timetable.maxConnect ?? 240;
  const itineraries = [];
  const seen = new Set();
  const add = (legs, waits = []) => {
    const key = itineraryKey(legs);
    if (seen.has(key)) return;
    seen.add(key);
    itineraries.push({
      legs,
      waits,
      stops: legs.length - 1,
      dest: legs.at(-1).dest,
      departureMinute: toMinutes(legs[0].dep),
      totalMinutes: legs.reduce(
        (total, leg) => total + flightDurationMinutes(leg, timezoneByCode),
        waits.reduce((total, wait) => total + wait, 0)
      ),
    });
  };

  const firstLegs = flightsByOrigin.get(origin) || [];
  firstLegs.forEach((leg) => add([leg]));
  for (const first of firstLegs) {
    if (!hubCodes.has(first.dest)) continue;
    for (const second of flightsByOrigin.get(first.dest) || []) {
      if (second.dest === origin) continue;
      const firstWait = waitMinutes(first.arr, second.dep);
      if (firstWait < minConnect || firstWait > maxConnect) continue;
      add([first, second], [firstWait]);
      if (!hubCodes.has(second.dest) || second.dest === first.dest) continue;
      for (const third of flightsByOrigin.get(second.dest) || []) {
        if ([origin, first.dest].includes(third.dest)) continue;
        const secondWait = waitMinutes(second.arr, third.dep);
        if (secondWait < minConnect || secondWait > maxConnect) continue;
        add([first, second, third], [firstWait, secondWait]);
      }
    }
  }
  return itineraries;
}

export function selectItineraries(itineraries, connectionFilter = "all") {
  const byDestination = new Map();
  itineraries.forEach((itinerary) => {
    if (!byDestination.has(itinerary.dest)) byDestination.set(itinerary.dest, []);
    byDestination.get(itinerary.dest).push(itinerary);
  });
  const selected = [];
  for (const list of byDestination.values()) {
    const nonstops = list.filter((item) => item.stops === 0);
    const oneStops = list
      .filter((item) => item.stops === 1)
      .sort((a, b) => a.totalMinutes - b.totalMinutes)
      .slice(0, 6);
    selected.push(...nonstops);
    if (connectionFilter === "nonstop") continue;
    selected.push(...oneStops);
    if (connectionFilter === "max1") continue;
    const remaining = Math.max(0, 6 - nonstops.length - oneStops.length);
    selected.push(
      ...list
        .filter((item) => item.stops === 2)
        .sort((a, b) => a.totalMinutes - b.totalMinutes)
        .slice(0, remaining)
    );
  }
  return selected.sort(
    (a, b) => a.dest.localeCompare(b.dest) || a.departureMinute - b.departureMinute || a.totalMinutes - b.totalMinutes
  );
}

export function passengerStandFindings(operatingReport, cityCode) {
  const check = operatingReport.checks.find((item) => item.id === "passenger_touch_on_stand");
  return (check?.findings || []).filter((finding) => finding.evidence?.city === cityCode);
}

export function instructionId(reference) {
  return String(reference).trim().toLowerCase().replace("§", "section-")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function instructionReferenceTokens(value) {
  return String(value).match(/§\d+(?:\.\d+)?[a-z]?(?:\s+Check\s+[A-Z]|\s+hard-stop addition)?|Lesson\s+\d+[a-z]?/gi) || [];
}

export function claimMatchesPassengerStandFinding(cityCode, claim, findings) {
  if (claim.rowType !== "stand") return false;
  return findings.some((finding) => {
    const evidence = finding.evidence || {};
    return evidence.city === cityCode
      && evidence.label === claim.label
      && evidence.kind === claim.kind
      && Number(evidence.start) === Number(claim.start)
      && Number(evidence.end) === Number(claim.end);
  });
}

export function scheduleMetrics(canonical) {
  const legs = canonical.legs;
  return {
    flights: legs.length,
    cities: new Set(legs.flatMap((leg) => [leg.origin, leg.destination])).size,
    routes: new Set(legs.map((leg) => leg.route)).size,
    lines: new Set(legs.map((leg) => leg.line)).size,
    markets: new Set(legs.map((leg) => `${leg.origin}-${leg.destination}`)).size,
  };
}

export function fleetUsage(canonical) {
  const usage = new Map();
  for (const leg of canonical.legs) {
    if (!usage.has(leg.fleet)) usage.set(leg.fleet, new Set());
    usage.get(leg.fleet).add(`${leg.line}:${leg.day}`);
  }
  return Object.fromEntries([...usage].map(([fleet, days]) => [fleet, days.size]));
}

export function legMatches(leg, query, filters = {}) {
  if (typeof filters === "string") filters = { fleet: filters };
  if (filters.fleet && leg.fleet !== filters.fleet) return false;
  if (filters.line && leg.line !== filters.line) return false;
  if (filters.origin && leg.origin !== filters.origin) return false;
  if (filters.destination && leg.destination !== filters.destination) return false;
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const exact = needle.match(/^(flight|route|line):\s*(.+)$/);
  if (exact) {
    return String(leg[exact[1]]).toLowerCase() === exact[2];
  }
  return [
    leg.flight,
    leg.route,
    leg.line,
    leg.day,
    leg.pairing,
    leg.origin,
    leg.destination,
    leg.fleet,
  ].some((value) => String(value).toLowerCase().includes(needle));
}

export function marketMatches(market, filters = {}) {
  const endpoints = [market.origin, market.destination];
  const airportsMatch = filters.origin && filters.destination
    ? filters.origin !== filters.destination
      && endpoints.includes(filters.origin)
      && endpoints.includes(filters.destination)
    : (!filters.origin || endpoints.includes(filters.origin))
      && (!filters.destination || endpoints.includes(filters.destination));
  return (!filters.fleet || market.fleet === filters.fleet) && airportsMatch;
}

export function flattenFrequencyMarkets(plan) {
  return plan.markets.flatMap((market) => market.allocations.map((fleet) => ({
    ...market,
    ...fleet,
  })));
}

export function extractReferences(evidence) {
  const references = {
    flights: new Set(),
    routes: new Set(),
    lines: new Set(),
    cities: new Set(),
    fleets: new Set(),
  };
  const cityKeys = new Set([
    "city",
    "origin",
    "destination",
    "terminator",
    "originator",
    "hub",
  ]);
  const walk = (value, key = "") => {
    if (Array.isArray(value)) {
      value.forEach((item) => walk(item, key));
      return;
    }
    if (value && typeof value === "object") {
      Object.entries(value).forEach(([childKey, child]) => walk(child, childKey));
      return;
    }
    const lower = key.toLowerCase();
    if (cityKeys.has(key) && typeof value === "string" && /^[A-Z0-9]{3,4}$/.test(value)) {
      references.cities.add(value);
    } else if (lower.includes("flight") && Number.isInteger(Number(value))) {
      references.flights.add(Number(value));
    } else if (key === "route" && Number.isInteger(Number(value))) {
      references.routes.add(Number(value));
    } else if (key === "line" && value !== null && value !== "") {
      references.lines.add(String(value));
    } else if (key === "fleet" && value !== null && value !== "") {
      references.fleets.add(String(value));
    }
  };
  walk(evidence);
  return Object.fromEntries(
    Object.entries(references).map(([key, values]) => [key, [...values].sort()])
  );
}

export function splitClaimSegments(start, end, windowStart = 0) {
  const numericStart = Number(start);
  const numericEnd = Number(end);
  const duration = Math.max(0, numericEnd - numericStart);
  if (duration >= 1440) return [{ start: 0, duration: 1440 }];
  const windowEnd = Number(windowStart) + 1440;
  const segments = [];
  const firstShift = Math.floor((Number(windowStart) - numericEnd) / 1440);
  const lastShift = Math.ceil((windowEnd - numericStart) / 1440);
  for (let shift = firstShift; shift <= lastShift; shift += 1) {
    const shiftedStart = numericStart + shift * 1440;
    const shiftedEnd = numericEnd + shift * 1440;
    const overlapStart = Math.max(Number(windowStart), shiftedStart);
    const overlapEnd = Math.min(windowEnd, shiftedEnd);
    if (overlapEnd > overlapStart) {
      segments.push({
        start: overlapStart - Number(windowStart),
        duration: overlapEnd - overlapStart,
      });
    }
  }
  return segments.sort((a, b) => a.start - b.start);
}

function metricCard(label, value, note, variant = "") {
  return `<article class="metric-card ${variant}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></article>`;
}

function statusLabel(status) {
  return {
    fail: "Blocking",
    warning: "Warning",
    not_evaluated: "Not evaluated",
    overridden: "Overridden",
    pass: "Passing",
  }[status] || status.replaceAll("_", " ");
}

function activateTab(tab, updateHash = true) {
  const valid = ["overview", "setup", "planning", "routings", "validation", "instructions", "timetable", "gates"];
  if (!valid.includes(tab)) tab = "overview";
  $$("[data-tab]").forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  $$("[data-view]").forEach((view) => {
    const active = view.dataset.view === tab;
    view.hidden = !active;
    view.classList.toggle("is-active", active);
  });
  if (updateHash) history.replaceState(null, "", `#${tab}`);
  $("#workspace").focus({ preventScroll: true });
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

async function loadSchedule(scheduleId) {
  const entry = state.manifest.schedules.find((item) => item.id === scheduleId);
  if (!entry) throw new Error(`Schedule ${scheduleId} is not in the site manifest.`);
  const fileEntries = Object.entries(entry.files);
  const loaded = await Promise.all(fileEntries.map(([, path]) => fetchJson(path)));
  const data = Object.fromEntries(fileEntries.map(([key], index) => [key, loaded[index]]));
  Object.assign(state, {
    scheduleEntry: entry,
    canonical: data.canonical,
    structural: data.structuralValidation,
    operating: data.operatingValidation,
    planning: data.planning,
    planningValidation: data.planningValidation,
    demandPlan: data.demandPlan,
    frequencyFleetPlan: data.frequencyFleetPlan,
    hubBankPlan: data.hubBankPlan,
    aircraftRoutePlan: data.aircraftRoutePlan,
    routingRepairPlan: data.routingRepairPlan,
    bankMaterializationDiagnostic: data.bankMaterializationDiagnostic,
    exactMaterializationPlan: data.exactMaterializationPlan,
    timetable: data.timetable,
    gates: data.gates,
    routingPage: 1,
    planningPage: 1,
    timetablePage: 1,
    itineraryCache: new Map(),
    buildConfig: null,
    buildPreflight: null,
  });
  renderAll();
}

async function initialize() {
  try {
    state.manifest = await fetchJson("schedules.json");
    state.instructions = await fetchJson(state.manifest.instructions.catalog);
    const select = $("#schedule-select");
    select.innerHTML = state.manifest.schedules
      .map((entry) => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.label)}</option>`)
      .join("");
    select.value = state.manifest.defaultScheduleId;
    select.disabled = false;
    await loadSchedule(select.value);
    $("#loading-state").hidden = true;
    $("#app").hidden = false;
    activateTab(location.hash.slice(1) || "overview", false);
  } catch (error) {
    $("#loading-state").hidden = true;
    $("#error-message").textContent = error.message;
    $("#error-state").hidden = false;
  }
}

function renderAll() {
  const previewWarning = $("#preview-warning");
  const previewNotice = state.scheduleEntry?.previewNotice;
  previewWarning.hidden = !previewNotice;
  previewWarning.textContent = previewNotice || "";
  ensureBuildConfig();
  renderOverview();
  renderSetup();
  populateFilters();
  renderPlanning();
  renderRoutings();
  renderValidation();
  renderInstructions();
  renderTimetable();
  renderGates();
}

function renderOverview() {
  const { canonical, structural, operating } = state;
  const schedule = canonical.schedule;
  const metrics = scheduleMetrics(canonical);
  $("#schedule-title").textContent = `Schedule ${schedule.number} · Version ${schedule.version}`;
  $("#schedule-note").textContent = schedule.label;
  $("#schedule-status").textContent = schedule.status.replaceAll("_", " ");
  $("#validation-count").textContent = operating.summary.effectiveErrorFindings;
  $("#overview-metrics").innerHTML = [
    metricCard("Flights", metrics.flights.toLocaleString(), "Published daily legs"),
    metricCard("Cities", metrics.cities, "Active network stations"),
    metricCard("Routes", metrics.routes, "Canonical aircraft routes"),
    metricCard("Lines", metrics.lines, "Ten-day aircraft lines"),
    metricCard(
      "Structural checks",
      `${structural.summary.passed}/${structural.summary.checks}`,
      "Migration fidelity",
      structural.status === "pass" ? "is-success" : "is-danger"
    ),
  ].join("");

  const usage = fleetUsage(canonical);
  $("#fleet-list").innerHTML = Object.entries(schedule.fleetCounts)
    .map(([fleet, capacity]) => {
      const used = usage[fleet] || 0;
      const percentage = capacity ? Math.min(100, (used / capacity) * 100) : 0;
      return `<div class="fleet-row"><span class="fleet-name">${escapeHtml(fleet)}</span><div class="progress-track" role="progressbar" aria-label="${escapeHtml(fleet)} utilization" aria-valuemin="0" aria-valuemax="${capacity}" aria-valuenow="${used}"><div class="progress-fill ${percentage >= 100 ? "is-full" : ""}" style="width:${percentage}%"></div></div><span class="fleet-value"><strong>${used}</strong> / ${capacity}</span></div>`;
    })
    .join("");

  const summary = operating.summary;
  $("#validation-snapshot").innerHTML = `
    <div class="snapshot-grid">
      <div class="snapshot-item error"><strong>${summary.effectiveErrorFindings}</strong><span>Blocking findings</span></div>
      <div class="snapshot-item warning"><strong>${summary.effectiveWarningFindings}</strong><span>Review warnings</span></div>
      <div class="snapshot-item unknown"><strong>${summary.notEvaluated}</strong><span>Unavailable checks</span></div>
    </div>${renderHardStop()}`;

  const failures = operating.checks
    .filter((check) => check.status === "fail")
    .sort((a, b) => b.metrics.effectiveFindingCount - a.metrics.effectiveFindingCount)
    .slice(0, 3);
  $("#attention-list").innerHTML = failures
    .map((check) => `<button class="attention-item text-button" type="button" data-open-check="${escapeHtml(check.id)}"><span class="attention-number">${check.metrics.effectiveFindingCount}</span><span><span class="attention-title">${escapeHtml(check.title)}</span><span class="attention-copy">${escapeHtml(check.section)} · ${escapeHtml(check.message)}</span></span></button>`)
    .join("");
}

function renderHardStop() {
  const check = state.operating.checks.find((item) => item.id === "departure_windows");
  const failing = check.status === "fail";
  return `<div class="hard-stop-card ${failing ? "is-fail" : ""}"><strong>${failing ? "Hard stop: curfew violation" : "Curfews: clear"}</strong><p>${escapeHtml(check.message)}. Curfew findings cannot be overridden.</p></div>`;
}

function populateSelect(select, values, firstLabel) {
  const current = select.value;
  select.innerHTML = `<option value="">${escapeHtml(firstLabel)}</option>${values
    .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    .join("")}`;
  if (values.includes(current)) select.value = current;
}

function populateFilters() {
  const fleets = [...new Set(state.canonical.legs.map((leg) => leg.fleet))].sort();
  const cities = state.canonical.cities.filter((city) => city.active).map((city) => city.code).sort();
  const lines = [...new Set(state.canonical.legs.map((leg) => leg.line))].sort();
  populateSelect($("#routing-fleet"), fleets, "All fleets");
  populateSelect($("#routing-line"), lines, "All lines");
  populateSelect($("#routing-origin"), cities, "Any airport");
  populateSelect($("#routing-destination"), cities, "Any airport");
  populateSelect($("#timetable-fleet"), fleets, "All fleets");
  populateSelect($("#timetable-origin"), cities, "Any origin");
  populateSelect($("#timetable-destination"), cities, "Any destination");
  populateSelect($("#planning-fleet"), Object.keys(state.frequencyFleetPlan.fleetPlan).sort(), "All fleets");
  populateSelect($("#planning-origin"), cities, "Any airport");
  populateSelect($("#planning-destination"), cities, "Any airport");

  const gateSelect = $("#gate-airport");
  const previous = gateSelect.value;
  const ordered = [...state.gates.cities].sort((a, b) => {
    const rankA = a.isHub ? 0 : a.isFocusCity ? 1 : 2;
    const rankB = b.isHub ? 0 : b.isFocusCity ? 1 : 2;
    return rankA - rankB || a.code.localeCompare(b.code);
  });
  gateSelect.innerHTML = ordered
    .map((city) => `<option value="${escapeHtml(city.code)}">${escapeHtml(city.code)} · ${escapeHtml(city.name)}</option>`)
    .join("");
  gateSelect.value = previous && ordered.some((city) => city.code === previous) ? previous : "PHF";
}

function renderPlanning() {
  const plan = state.planning;
  const validation = state.planningValidation;
  const demand = state.demandPlan;
  const allocation = state.frequencyFleetPlan;
  const bankPlan = state.hubBankPlan;
  const routing = state.aircraftRoutePlan;
  const repair = state.routingRepairPlan;
  const materialization = state.bankMaterializationDiagnostic;
  const exact = state.exactMaterializationPlan;
  const topologyReady = validation.status === "pass" && demand.status === "pass" && allocation.status === "pass" && bankPlan.status === "pass" && repair.status === "pass";
  const ready = topologyReady && exact.materializationStatus === "complete";
  $("#planning-status").textContent = ready ? "Exact cycles pass · candidate canonicalization enabled" : exact.materializationStatus === "blocked" ? "Exact materialization blocked" : materialization.materializationStatus === "blocked" ? "Bank materialization blocked" : topologyReady ? "Bank-window lower bound passes · exact cycles pending" : "Routing repair required";
  $("#planning-status").classList.toggle("is-danger", !topologyReady || materialization.materializationStatus === "blocked" || exact.materializationStatus === "blocked");
  $("#planning-metrics").innerHTML = [
    metricCard("Proposed legs", allocation.summary.plannedLegs.toLocaleString(), `${allocation.summary.optionalRoundTrips.toLocaleString()} demand-allocated round trips above minimums`),
    metricCard("Candidate markets", allocation.summary.candidateMarkets.toLocaleString(), `${allocation.summary.newRequiredHubMarkets} required hub markets added; ${plan.summary.legCount.toLocaleString()} historical legs retained for comparison`),
    metricCard("Point-to-point", `${(allocation.summary.pointToPointShare * 100).toFixed(1)}%`, `${allocation.summary.pointToPointLegs.toLocaleString()} proposed legs`, allocation.summary.pointToPointShare <= 0.1 ? "is-success" : "is-danger"),
    metricCard("Demand coverage", `${demand.matrix.airportCount}/${state.canonical.cities.filter((city) => city.active).length}`, "Active airport O-D roster", demand.status === "pass" ? "is-success" : "is-danger"),
    metricCard("Hub assignment parity", `${demand.assignmentParity.matched}/${demand.assignmentParity.compared}`, "Golden multi-hub result", demand.assignmentParity.differences.length ? "is-danger" : "is-success"),
    metricCard("Banked hub legs", `${bankPlan.summary.placedLegs.toLocaleString()}/${bankPlan.summary.hubMarketLegs.toLocaleString()}`, `${bankPlan.summary.banks} banks · ${bankPlan.summary.curfewViolations} curfew violations`, bankPlan.status === "pass" ? "is-success" : "is-danger"),
    metricCard("Routed legs", `${repair.summary.routedLegs.toLocaleString()}/${repair.summary.plannedLegs.toLocaleString()}`, `${repair.summary.curfewViolations} curfew violations · ${repair.summary.destinationsWithoutRon} RON gaps`, repair.status === "pass" ? "is-success" : "is-danger"),
    metricCard("First-pass timing", `${routing.summary.requiredAircraft}/${routing.summary.configuredAircraft}`, `${routing.summary.aircraftShortfall} aircraft above the selected fleet`, "is-danger"),
    metricCard("Repaired fleet fit", `${repair.summary.requiredAircraft}/${repair.summary.configuredAircraft}`, `${repair.summary.remainingAircraft} schedule-selected aircraft remain`, repair.summary.aircraftShortfall ? "is-danger" : "is-success"),
    metricCard("Bank + RON lower bound", `${materialization.summary.bankAndRonMinimumAircraft}/${materialization.summary.configuredAircraft}`, `${materialization.summary.bankWindowLowerBoundHeadroom} lower-bound headroom · ${materialization.summary.nonHubLegs} non-hub legs still pending`, materialization.summary.fleetAllocationShortfall ? "is-danger" : "is-success"),
    metricCard("Exact materialization", `${exact.summary.routedLegs.toLocaleString()}/${exact.summary.plannedLegs.toLocaleString()}`, `${exact.summary.requiredAircraft}/${exact.summary.configuredAircraft} aircraft · ${exact.summary.nonHubIntegratedLegs} non-hub legs integrated`, exact.status === "pass" ? "is-success" : "is-danger"),
  ].join("");
  $("#allocation-checks").innerHTML = allocation.checks
    .map((check) => `<article class="${check.status === "pass" ? "is-pass" : "is-fail"}"><strong>${check.status === "pass" ? "Pass" : "Blocked"}</strong><span>${escapeHtml(check.message)}</span></article>`)
    .join("");
  $("#bank-placement-checks").innerHTML = bankPlan.checks
    .map((check) => `<article class="${check.status === "pass" ? "is-pass" : "is-fail"}"><strong>${check.status === "pass" ? "Pass" : check.hardStop ? "Hard stop" : "Blocked"}</strong><span>${escapeHtml(check.message)}</span></article>`)
    .join("");
  $("#aircraft-routing-checks").innerHTML = [...repair.checks, ...materialization.checks, ...exact.checks]
    .map((check) => `<article class="${check.status === "pass" ? "is-pass" : check.status === "pending" ? "is-pending" : "is-fail"}"><strong>${check.status === "pass" ? "Pass" : check.status === "pending" ? "Pending" : check.hardStop ? "Hard stop" : "Blocked"}</strong><span>${escapeHtml(check.message)}</span></article>`)
    .join("") + `<article class="is-pending"><strong>Next step</strong><span>${escapeHtml(exact.nextStep.message)}</span></article>`;
  $("#hub-bank-rows").innerHTML = flattenBankWindows(bankPlan)
    .map((bank) => `<tr><td><strong>${escapeHtml(bank.hub)}</strong></td><td>${escapeHtml(bank.id)}</td><td>${formatMinute24(bank.startMinute)}–${formatMinute24(bank.endMinute)}</td><td>${formatMinute24(bank.arrivalTargetMinute)}</td><td>${formatMinute24(bank.departureTargetMinute)}</td><td>${bank.arrivalCount}</td><td>${bank.departureCount}</td></tr>`)
    .join("");

  $("#planning-fleet-rows").innerHTML = Object.entries(allocation.fleetPlan)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([fleet, row]) => `<tr><td><span class="fleet-badge">${escapeHtml(fleet)}</span></td><td>${row.aircraftCount}</td><td>${row.marketCount}</td><td>${row.legCount.toLocaleString()}</td><td>${formatDuration(row.plannedAircraftMinutes)}</td><td>${formatDuration(row.availableAircraftMinutes)}</td><td><strong>${(row.utilization * 100).toFixed(1)}%</strong></td></tr>`)
    .join("");
  $("#routing-fleet-rows").innerHTML = Object.entries(repair.fleetPlan)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([fleet, row]) => { const bankRow = materialization.fleetPlan[fleet]; const exactRow = exact.fleetPlan[fleet]; return `<tr><td><span class="fleet-badge">${escapeHtml(fleet)}</span></td><td>${row.configuredAircraft}</td><td>${routing.fleetPlan[fleet]?.requiredAircraft ?? "—"}</td><td>${row.requiredAircraft}</td><td>${bankRow.bankAndRonMinimumAircraft}</td><td><strong class="${exactRow.shortfall ? "danger-text" : ""}">${exactRow.requiredAircraft}</strong></td><td><strong class="${exactRow.shortfall ? "danger-text" : ""}">${formatRemainingAircraft(exactRow)}</strong></td><td>${exactRow.cycles}</td><td>${exactRow.routedLegs.toLocaleString()}</td></tr>`; })
    .join("");
  $("#planning-limitations").innerHTML = [...allocation.limitations, ...bankPlan.limitations, ...routing.limitations, ...repair.limitations, ...materialization.limitations, ...exact.limitations]
    .map((item) => `<article><strong>Known boundary</strong><span>${escapeHtml(item)}</span></article>`)
    .join("");

  const demandCities = [...demand.multiHubAssignments.cities]
    .sort((a, b) => b.marketSize - a.marketSize || a.code.localeCompare(b.code));
  $("#demand-city-rows").innerHTML = demandCities
    .map((city) => `<tr><td><strong>${escapeHtml(city.code)}</strong></td><td>${city.marketSize.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td><td>${city.percentile.toFixed(1)}</td><td>${city.maximumHubs}</td><td>${city.hubAssignments.map(escapeHtml).join(" / ")}</td><td><span class="parity-badge ${city.matchesExpected ? "is-match" : "is-difference"}">${city.matchesExpected ? "Match" : "Different"}</span></td></tr>`)
    .join("");

  const filters = {
    fleet: $("#planning-fleet").value,
    origin: $("#planning-origin").value,
    destination: $("#planning-destination").value,
  };
  const proposedRows = flattenFrequencyMarkets(allocation);
  const rows = proposedRows.filter((market) => marketMatches(market, filters));
  const paged = paginate(rows, state.planningPage);
  state.planningPage = paged.page;
  $("#planning-market-count").textContent = `${rows.length.toLocaleString()} rows`;
  $("#planning-market-rows").innerHTML = paged.rows.length
    ? paged.rows.map((market) => `<tr><td><span class="fleet-badge">${escapeHtml(market.fleet)}</span></td><td><strong>${escapeHtml(market.origin)}</strong></td><td><strong>${escapeHtml(market.destination)}</strong></td><td>${escapeHtml(market.classification.replaceAll("_", " "))}</td><td>${market.twoWayDemand.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td><td>${market.roundTrips}</td><td><strong>${market.legCount}</strong></td><td>${market.historicalLegs}</td></tr>`).join("")
    : `<tr class="empty-row"><td colspan="8">No planning rows match these filters.</td></tr>`;
  renderPagination($("#planning-pagination"), "planning", rows.length, paged.page, paged.pageCount);
}

export function flattenBankWindows(plan) {
  return plan.hubs.flatMap((hub) => hub.banks.map((bank) => ({ hub: hub.hub, ...bank })));
}

export function formatRemainingAircraft(row) {
  return row.shortfall ? `Short ${row.shortfall}` : String(row.remainingAircraft);
}

export function paginate(items, page, pageSize = DEFAULT_PAGE_SIZE) {
  const size = pageSize === "all" ? Math.max(1, items.length) : Number(pageSize);
  const pageCount = Math.max(1, Math.ceil(items.length / size));
  const safePage = Math.min(Math.max(1, page), pageCount);
  return {
    page: safePage,
    pageCount,
    pageSize,
    rows: items.slice((safePage - 1) * size, safePage * size),
  };
}

function renderPagination(container, context, total, page, pageCount, pageSize = DEFAULT_PAGE_SIZE) {
  const size = pageSize === "all" ? Math.max(1, total) : Number(pageSize);
  const start = total ? (page - 1) * size + 1 : 0;
  const end = Math.min(total, page * size);
  const summary = pageSize === "all"
    ? `Showing all ${total.toLocaleString()}`
    : `Showing ${start.toLocaleString()}–${end.toLocaleString()} of ${total.toLocaleString()}`;
  container.innerHTML = `<span>${summary}</span><div class="pagination-buttons"><button type="button" data-page-context="${context}" data-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>Previous</button><button type="button" data-page-context="${context}" data-page="${page + 1}" ${page >= pageCount ? "disabled" : ""}>Next</button></div>`;
}

function renderRoutings() {
  const query = $("#routing-search").value;
  const filters = {
    fleet: $("#routing-fleet").value,
    line: $("#routing-line").value,
    origin: $("#routing-origin").value,
    destination: $("#routing-destination").value,
  };
  const filtered = state.canonical.legs.filter((leg) => legMatches(leg, query, filters));
  const paged = paginate(filtered, state.routingPage, state.routingPageSize);
  state.routingPage = paged.page;
  $("#routing-result-count").textContent = `${filtered.length.toLocaleString()} flights`;
  $("#routing-rows").innerHTML = paged.rows.length
    ? paged.rows.map((leg) => `<tr id="flight-${leg.flight}"><td class="route-number">${leg.route}</td><td><strong>${escapeHtml(leg.line)}</strong> / ${leg.day}</td><td>${leg.sequenceWithinRoute}</td><td class="flight-number">${leg.flight}</td><td><strong>${escapeHtml(leg.origin)}</strong><span class="market-arrow">→</span><strong>${escapeHtml(leg.destination)}</strong></td><td>${escapeHtml(leg.departure)}–${escapeHtml(leg.arrival)}</td><td><span class="fleet-badge">${escapeHtml(leg.fleet)}</span></td></tr>`).join("")
    : `<tr class="empty-row"><td colspan="7">No routings match these filters.</td></tr>`;
  renderPagination($("#routing-pagination"), "routing", filtered.length, paged.page, paged.pageCount, state.routingPageSize);
}

function timetableMatches(flight) {
  const query = $("#timetable-search").value.trim().toLowerCase();
  return (!query || [flight.flight, flight.origin, flight.dest, flight.fleet].some((value) => String(value).toLowerCase().includes(query)))
    && (!$("#timetable-origin").value || flight.origin === $("#timetable-origin").value)
    && (!$("#timetable-destination").value || flight.dest === $("#timetable-destination").value)
    && (!$("#timetable-fleet").value || flight.fleet === $("#timetable-fleet").value);
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours ? `${hours}h ` : ""}${remainder}m`;
}

function cityName(code) {
  const city = state.timetable.cities.find((item) => item.code === code);
  return city ? city.name : code;
}

function itinerariesFrom(origin) {
  if (!state.itineraryCache.has(origin)) {
    const hubCodes = new Set(
      state.canonical.cities
        .filter((city) => city.role === "hub")
        .map((city) => city.code)
    );
    CONNECTIONS_HUB_OVERRIDE.forEach((code) => hubCodes.add(code));
    const timezoneByCode = Object.fromEntries(
      state.canonical.cities.map((city) => [city.code, city.timezone])
    );
    state.itineraryCache.set(
      origin,
      buildItineraries(state.timetable, origin, hubCodes, timezoneByCode)
    );
  }
  return state.itineraryCache.get(origin);
}

function itineraryMatchesFilters(itinerary) {
  const destination = $("#timetable-destination").value;
  const fleet = $("#timetable-fleet").value;
  const query = $("#timetable-search").value.trim().toLowerCase();
  if (destination && itinerary.dest !== destination) return false;
  if (fleet && !itinerary.legs.some((leg) => leg.fleet === fleet)) return false;
  if (!query) return true;
  return [itinerary.dest, cityName(itinerary.dest), ...itinerary.legs.flatMap((leg) => [leg.flight, leg.origin, leg.dest, leg.fleet])]
    .some((value) => String(value).toLowerCase().includes(query));
}

function renderItinerary(itinerary) {
  const stopLabel = itinerary.stops === 0 ? "Non-stop" : `${itinerary.stops} stop${itinerary.stops === 1 ? "" : "s"}`;
  const variant = itinerary.stops === 0 ? "is-nonstop" : itinerary.stops === 2 ? "is-two-stop" : "";
  const legs = itinerary.legs.map((leg, index) => {
    const connection = index > 0
      ? `<span class="connection-note">Connect at ${escapeHtml(leg.origin)} · ${formatDuration(itinerary.waits[index - 1])}</span>`
      : "";
    return `${connection}<div class="itinerary-leg"><span class="flight-number">${leg.flight}</span><span><strong>${escapeHtml(leg.origin)}</strong><span class="market-arrow">→</span><strong>${escapeHtml(leg.dest)}</strong></span><span class="itinerary-time">${escapeHtml(leg.dep)}–${escapeHtml(leg.arr)}</span><span class="fleet-badge">${escapeHtml(leg.fleet)}</span></div>`;
  }).join("");
  return `<article class="itinerary-card ${variant}"><div class="itinerary-summary"><strong>${stopLabel}</strong><span>${escapeHtml(itinerary.legs[0].dep)} departure · ${formatDuration(itinerary.totalMinutes)} total travel</span></div><div class="itinerary-legs">${legs}</div></article>`;
}

function renderItineraryResults(itineraries) {
  if (!itineraries.length) {
    return `<div class="itinerary-empty">No itineraries match these filters and the ${state.timetable.minConnect}–${state.timetable.maxConnect} minute connection window.</div>`;
  }
  const grouped = new Map();
  itineraries.forEach((itinerary) => {
    if (!grouped.has(itinerary.dest)) grouped.set(itinerary.dest, []);
    grouped.get(itinerary.dest).push(itinerary);
  });
  return [...grouped]
    .sort(([a], [b]) => cityName(a).localeCompare(cityName(b)))
    .map(([destination, options]) => `<section class="itinerary-destination"><div class="itinerary-heading"><h2>${escapeHtml(cityName(destination))} <span>${escapeHtml(destination)}</span></h2><span>${options.length} option${options.length === 1 ? "" : "s"}</span></div><div class="itinerary-list">${options.map(renderItinerary).join("")}</div></section>`)
    .join("");
}

function renderTimetable() {
  const origin = $("#timetable-origin").value;
  const connectionFilter = $("#timetable-connections").value;
  $("#connection-window").textContent = `${state.timetable.minConnect}–${state.timetable.maxConnect} minute connection window`;
  $("#timetable-connections").disabled = !origin;
  if (origin) {
    const itineraries = selectItineraries(itinerariesFrom(origin), connectionFilter)
      .filter(itineraryMatchesFilters);
    $("#timetable-result-count").textContent = `${itineraries.length.toLocaleString()} itineraries`;
    $("#timetable-mode-note").textContent = `Showing travel options from ${cityName(origin)} (${origin}). Non-stops are always included; up to six shortest one-stop options are shown per destination.`;
    $("#itinerary-results").innerHTML = renderItineraryResults(itineraries);
    $("#itinerary-results").hidden = false;
    $("#timetable-flight-shell").hidden = true;
    $("#timetable-pagination").hidden = true;
    return;
  }

  const filtered = sortFlightsByDeparture(state.timetable.flights.filter(timetableMatches));
  const paged = paginate(filtered, state.timetablePage);
  state.timetablePage = paged.page;
  $("#timetable-mode-note").textContent = "Select an origin to view connecting itineraries. With no origin selected, the complete flight list is sorted by departure time.";
  $("#timetable-result-count").textContent = `${filtered.length.toLocaleString()} flights`;
  $("#itinerary-results").hidden = true;
  $("#timetable-flight-shell").hidden = false;
  $("#timetable-pagination").hidden = false;
  $("#timetable-rows").innerHTML = paged.rows.length
    ? paged.rows.map((flight) => `<tr><td class="flight-number">${flight.flight}</td><td><strong>${escapeHtml(flight.origin)}</strong></td><td>${escapeHtml(flight.dep)}</td><td><strong>${escapeHtml(flight.dest)}</strong></td><td>${escapeHtml(flight.arr)}</td><td><span class="fleet-badge">${escapeHtml(flight.fleet)}</span></td></tr>`).join("")
    : `<tr class="empty-row"><td colspan="6">No timetable flights match these filters.</td></tr>`;
  renderPagination($("#timetable-pagination"), "timetable", filtered.length, paged.page, paged.pageCount);
}

function findingLinks(finding) {
  const refs = extractReferences(finding.evidence);
  const links = [];
  refs.flights.slice(0, 3).forEach((flight) => links.push(`<button class="finding-link" type="button" data-ref-type="flight" data-ref="${flight}">Flight ${flight}</button>`));
  refs.routes.slice(0, 2).forEach((route) => links.push(`<button class="finding-link" type="button" data-ref-type="route" data-ref="${route}">Route ${route}</button>`));
  refs.lines.slice(0, 2).forEach((line) => links.push(`<button class="finding-link" type="button" data-ref-type="line" data-ref="${escapeHtml(line)}">Line ${escapeHtml(line)}</button>`));
  refs.cities.slice(0, 3).forEach((city) => links.push(`<button class="finding-link" type="button" data-ref-type="city" data-ref="${escapeHtml(city)}">${escapeHtml(city)} gates</button>`));
  refs.fleets.slice(0, 2).forEach((fleet) => links.push(`<button class="finding-link" type="button" data-ref-type="fleet" data-ref="${escapeHtml(fleet)}">${escapeHtml(fleet)} routings</button>`));
  return links.length ? `<div class="finding-links">${links.join("")}</div>` : "";
}

function renderInstructionReferences(value) {
  const tokens = instructionReferenceTokens(value);
  if (!tokens.length) return escapeHtml(value);
  let rendered = "";
  let cursor = 0;
  tokens.forEach((token) => {
    const index = value.indexOf(token, cursor);
    rendered += escapeHtml(value.slice(cursor, index));
    const id = instructionId(token);
    const exists = state.instructions.entries.some((entry) => entry.id === id);
    rendered += exists
      ? `<button class="instruction-reference" type="button" data-instruction-id="${escapeHtml(id)}">${escapeHtml(token)}</button>`
      : `<span class="instruction-reference is-missing" title="Instruction text is not indexed">${escapeHtml(token)}</span>`;
    cursor = index + token.length;
  });
  return rendered + escapeHtml(value.slice(cursor));
}

function instructionKindLabel(kind) {
  return {
    section: "Section",
    lesson: "Standing lesson",
    check: "Section check",
    addition: "Instruction addition",
  }[kind] || kind;
}

function renderInstructions(requestedId = state.instructionId) {
  const query = $("#instruction-search").value.trim().toLowerCase();
  const kind = $("#instruction-kind").value;
  const entries = state.instructions.entries;
  const selected = entries.find((entry) => entry.id === requestedId)
    || entries.find((entry) => entry.id === state.instructionId)
    || entries[0];
  state.instructionId = selected.id;
  const filtered = entries.filter((entry) => {
    if (kind && entry.kind !== kind) return false;
    return !query || [entry.reference, entry.title, entry.text].join(" ").toLowerCase().includes(query);
  });
  $("#instruction-version").textContent = state.instructions.version;
  $("#instruction-result-count").textContent = `${filtered.length} reference${filtered.length === 1 ? "" : "s"}`;
  $("#instruction-list").innerHTML = filtered.length
    ? filtered.map((entry) => `<button type="button" class="instruction-list-item${entry.id === selected.id ? " is-active" : ""}" data-instruction-id="${escapeHtml(entry.id)}"><span>${escapeHtml(entry.reference)}</span><strong>${escapeHtml(entry.title)}</strong></button>`).join("")
    : `<p class="instruction-empty">No instruction references match this search.</p>`;
  $("#instruction-document").innerHTML = `<header class="instruction-document-heading"><div><p class="eyebrow">${escapeHtml(instructionKindLabel(selected.kind))}</p><h2>${escapeHtml(selected.reference)} · ${escapeHtml(selected.title)}</h2></div><a class="source-link" href="${escapeHtml(`${state.manifest.repositoryUrl}/blob/main/${selected.sourcePath}`)}" target="_blank" rel="noreferrer">Open Markdown source</a></header><pre class="instruction-text">${escapeHtml(selected.text)}</pre>`;
}

function openInstruction(instructionReferenceId) {
  state.instructionId = instructionReferenceId;
  $("#instruction-search").value = "";
  $("#instruction-kind").value = "";
  renderInstructions(instructionReferenceId);
  activateTab("instructions");
  $("#instruction-document").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderValidation(openCheckId = "") {
  const query = $("#validation-search").value.trim().toLowerCase();
  const status = $("#validation-status").value;
  $("#structural-banner").innerHTML = `<strong>Structural fidelity: ${state.structural.summary.passed}/${state.structural.summary.checks} checks passing</strong><span>Timetable and gate exports match the frozen v2.2.5 baseline byte for byte.</span>`;
  const checks = state.operating.checks.filter((check) => {
    if (status && check.status !== status) return false;
    if (!query) return true;
    return [check.title, check.section, check.message, JSON.stringify(check.findings)]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });
  $("#check-list").innerHTML = checks.length
    ? checks.map((check) => renderCheck(check, query, check.id === openCheckId)).join("")
    : `<div class="panel"><div class="check-body"><p class="check-message">No validation checks match these filters.</p></div></div>`;
  if (openCheckId) document.getElementById(`check-${openCheckId}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderCheck(check, query, forceOpen) {
  const effectiveCount = check.metrics.effectiveFindingCount ?? check.findings.length;
  const matching = query
    ? check.findings.filter((finding) => `${finding.message} ${JSON.stringify(finding.evidence)}`.toLowerCase().includes(query))
    : check.findings;
  const visible = matching.slice(0, 25);
  const findings = visible.length
    ? `<div class="finding-list">${visible.map((finding) => `<article class="finding-item"><p>${escapeHtml(finding.message)}</p>${findingLinks(finding)}<details><summary class="finding-more">Evidence</summary><pre>${escapeHtml(JSON.stringify(finding.evidence, null, 2))}</pre></details></article>`).join("")}</div>${matching.length > visible.length ? `<p class="finding-more">Showing 25 of ${matching.length} findings. Use search to narrow the list.</p>` : ""}`
    : "";
  return `<details class="check-card status-${check.status}" id="check-${escapeHtml(check.id)}" ${forceOpen ? "open" : ""}><summary><span class="check-title"><strong>${escapeHtml(check.title)}</strong><span>${renderInstructionReferences(check.section)} · ${effectiveCount} effective findings</span></span><span class="check-badges">${check.hardStop ? '<span class="hard-stop-badge">Hard stop</span>' : ""}<span class="check-status">${escapeHtml(statusLabel(check.status))}</span></span></summary><div class="check-body"><p class="check-message">${escapeHtml(check.message)}</p>${findings}</div></details>`;
}

function renderGates() {
  closeGateClaimDetails();
  const code = $("#gate-airport").value;
  const city = state.gates.cities.find((item) => item.code === code) || state.gates.cities[0];
  if (!city) return;
  const gateClaims = city.claims.filter((claim) => claim.rowType === "gate");
  const standClaims = city.claims.filter((claim) => claim.rowType === "stand");
  const passengerStandClaims = passengerStandFindings(state.operating, city.code);
  $("#gate-metrics").innerHTML = [
    metricCard("Airport", city.code, city.name),
    metricCard("Peak use", city.peakUsed, "Simultaneous aircraft", city.peakUsed > city.nGates + city.nStands ? "is-danger" : ""),
    metricCard("Gates", city.nGates, `${gateClaims.length} assigned claim pieces`),
    metricCard(
      "Stands",
      city.nStands,
      passengerStandClaims.length
        ? `${passengerStandClaims.length} passenger-handling conflict${passengerStandClaims.length === 1 ? "" : "s"}`
        : `${standClaims.length} assigned claim pieces · no passenger handling`,
      passengerStandClaims.length ? "is-danger" : ""
    ),
  ].join("");
  const colors = state.gates.fleetColors;
  $("#timeline-key").innerHTML = `${Object.entries(colors).map(([fleet, color]) => `<span class="legend-item"><i class="legend-swatch" style="background:${escapeHtml(color)}"></i>${escapeHtml(fleet)}</span>`).join("")}<span class="legend-item legend-warning"><i class="legend-swatch"></i>Passenger handling on stand</span>`;

  const maximumGateRow = Math.max(city.nGates, ...gateClaims.map((claim) => claim.row));
  const maximumStandRow = Math.max(city.nStands, ...standClaims.map((claim) => claim.row));
  const lanes = [
    ...Array.from({ length: maximumGateRow }, (_, index) => ({ type: "gate", row: index + 1 })),
    ...Array.from({ length: maximumStandRow }, (_, index) => ({ type: "stand", row: index + 1 })),
  ];
  const axis = Array.from({ length: 7 }, (_, index) => GATE_WINDOW_START + index * 240);
  $("#gate-timeline").innerHTML = `<div class="time-axis"><span></span><div class="axis-track">${axis.map((minute) => `<span class="axis-label" style="left:${((minute - GATE_WINDOW_START) / 1440) * 100}%">${formatMinute24(minute)}</span>`).join("")}</div></div>${lanes.map((lane) => renderLane(city, lane, colors, passengerStandClaims)).join("")}`;
}

function renderLane(city, lane, colors, passengerStandClaims) {
  const claims = city.claims.filter((claim) => claim.rowType === lane.type && claim.row === lane.row);
  const bars = claims.flatMap((claim) => {
    const passengerHandling = claimMatchesPassengerStandFinding(city.code, claim, passengerStandClaims);
    const fleetColor = colors[claim.fleet] || "#cbd5e1";
    const timeLabel = `${formatMinute24(claim.start)}–${formatMinute24(claim.end)}`;
    const accessibleLabel = `${claim.label}, ${claim.fleet}, ${claim.kind}, ${timeLabel}${passengerHandling ? ", passenger handling on a stand" : ""}`;
    return splitClaimSegments(claim.start, claim.end, GATE_WINDOW_START).map((segment) => `<button type="button" class="claim-bar kind-${lane.type}${passengerHandling ? " is-passenger-handling" : ""}" title="${escapeHtml(accessibleLabel)}" aria-label="${escapeHtml(accessibleLabel)}" aria-controls="claim-tooltip" aria-expanded="false" data-gate-claim data-claim-label="${escapeHtml(claim.label)}" data-claim-fleet="${escapeHtml(claim.fleet)}" data-claim-kind="${escapeHtml(claim.kind)}" data-claim-start="${escapeHtml(claim.start)}" data-claim-end="${escapeHtml(claim.end)}" data-claim-row-type="${escapeHtml(claim.rowType)}" data-claim-row="${escapeHtml(claim.row)}" data-claim-arrival-city="${escapeHtml(claim.arrivalCity || "")}" data-claim-departure-city="${escapeHtml(claim.departureCity || "")}" data-claim-passenger-handling="${passengerHandling}" style="--fleet-color:${escapeHtml(fleetColor)};left:${(segment.start / 1440) * 100}%;width:${Math.max(0.12, (segment.duration / 1440) * 100)}%;background:${escapeHtml(fleetColor)}">${escapeHtml(claim.label)}</button>`);
  }).join("");
  return `<div class="timeline-row"><span class="lane-label">${lane.type === "gate" ? "Gate" : "Stand"} ${lane.row}</span><div class="lane-track">${bars}</div></div>`;
}

function closeGateClaimDetails() {
  const tooltip = $("#claim-tooltip");
  if (!tooltip) return;
  $$('[data-gate-claim][aria-expanded="true"]').forEach((button) => button.setAttribute("aria-expanded", "false"));
  tooltip.hidden = true;
  tooltip.classList.remove("is-warning");
}

function toggleGateClaimDetails(button) {
  const tooltip = $("#claim-tooltip");
  const wasOpen = button.getAttribute("aria-expanded") === "true" && !tooltip.hidden;
  closeGateClaimDetails();
  if (wasOpen) return;

  const passengerHandling = button.dataset.claimPassengerHandling === "true";
  const position = `${button.dataset.claimRowType === "gate" ? "Gate" : "Stand"} ${button.dataset.claimRow}`;
  const movement = [button.dataset.claimArrivalCity, button.dataset.claimDepartureCity]
    .filter(Boolean)
    .join(` → ${$("#gate-airport").value} → `);
  $("#claim-tooltip-title").textContent = button.dataset.claimLabel;
  $("#claim-tooltip-summary").textContent = `${button.dataset.claimFleet} · ${button.dataset.claimKind.toUpperCase()} · ${formatMinute24(button.dataset.claimStart)}–${formatMinute24(button.dataset.claimEnd)} · ${position}`;
  $("#claim-tooltip-movement").textContent = movement;
  $("#claim-tooltip-warning").textContent = passengerHandling
    ? "Passenger handling occurs on this stand segment; a gate is required."
    : "";
  $("#claim-tooltip-warning").hidden = !passengerHandling;
  tooltip.classList.toggle("is-warning", passengerHandling);
  tooltip.hidden = false;
  button.setAttribute("aria-expanded", "true");
}

function setupStorageKey() {
  return `caa-scheduler:build-config:v1:${state.canonical.schedule.id}`;
}

function saveSetupDraft(message = "Saved in this browser") {
  try {
    localStorage.setItem(setupStorageKey(), serializeBuildConfig(state.buildConfig));
    $("#setup-status").textContent = message;
  } catch {
    $("#setup-status").textContent = "Local save unavailable";
  }
}

function ensureBuildConfig() {
  if (state.buildConfig) return;
  let loaded = null;
  try {
    const value = localStorage.getItem(setupStorageKey());
    if (value) loaded = normalizeBuildConfig(JSON.parse(value));
  } catch {
    loaded = null;
  }
  state.buildConfig = loaded || createBuildConfig(state.canonical, state.manifest);
  state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
}

function renderSetup() {
  const config = state.buildConfig;
  const values = {
    "#setup-number": config.schedule.number,
    "#setup-version": config.schedule.version,
    "#setup-label": config.schedule.label,
    "#setup-mode": config.schedule.mode,
    "#setup-start-kind": config.startingPoint.kind,
    "#setup-connect-min": config.connectionWindowMinutes.minimum,
    "#setup-connect-max": config.connectionWindowMinutes.maximum,
    "#setup-instruction-version": config.inputs.instructions.version,
    "#setup-instruction-source": config.inputs.instructions.source,
    "#setup-city-file": config.inputs.cityInformation.filename,
    "#setup-city-sha": config.inputs.cityInformation.sha256,
    "#setup-policy-file": config.inputs.operatingPolicy.filename,
    "#setup-policy-sha": config.inputs.operatingPolicy.sha256,
    "#setup-demand-version": config.inputs.demandData.version,
    "#setup-notes": config.notes,
  };
  Object.entries(values).forEach(([selector, value]) => { $(selector).value = value ?? ""; });

  $("#setup-baseline").innerHTML = state.manifest.schedules
    .map((entry) => `<option value="${escapeHtml(entry.id)}">${escapeHtml(entry.label)}</option>`)
    .join("");
  $("#setup-baseline").value = config.startingPoint.scheduleId || state.canonical.schedule.id;
  $("#setup-baseline").disabled = config.startingPoint.kind === "blank";

  $("#setup-fleet-rows").innerHTML = Object.entries(config.fleetCounts)
    .map(([fleet, count], index) => `<div class="setup-row fleet-setup-row" data-setup-fleet-row>
      <label><span>Fleet type</span><input type="text" value="${escapeHtml(fleet)}" data-setup-fleet-name aria-label="Fleet type ${index + 1}"></label>
      <label><span>Aircraft</span><input type="number" min="0" step="1" value="${escapeHtml(count)}" data-setup-fleet-count aria-label="${escapeHtml(fleet)} aircraft count"></label>
      <button class="row-remove" type="button" data-remove-fleet="${index}" aria-label="Remove ${escapeHtml(fleet)}">Remove</button>
    </div>`)
    .join("");

  $("#setup-network-rows").innerHTML = config.networkChanges.length
    ? config.networkChanges.map((change, index) => `<div class="setup-row network-setup-row" data-setup-network-row>
        <label><span>Airport</span><input type="text" maxlength="4" value="${escapeHtml(change.airport)}" data-network-airport aria-label="Airport code for change ${index + 1}"></label>
        <label><span>Action</span><select data-network-action aria-label="Action for ${escapeHtml(change.airport || `change ${index + 1}`)}">
          <option value="add" ${change.action === "add" ? "selected" : ""}>Add</option>
          <option value="remove" ${change.action === "remove" ? "selected" : ""}>Remove</option>
          <option value="status_change" ${change.action === "status_change" ? "selected" : ""}>Change status</option>
        </select></label>
        <label><span>Target status</span><select data-network-status aria-label="Target status for ${escapeHtml(change.airport || `change ${index + 1}`)}">
          <option value="">Not applicable</option>
          <option value="destination" ${change.targetStatus === "destination" ? "selected" : ""}>Destination</option>
          <option value="focus_city" ${change.targetStatus === "focus_city" ? "selected" : ""}>Focus city</option>
          <option value="hub" ${change.targetStatus === "hub" ? "selected" : ""}>Hub</option>
          <option value="inactive" ${change.targetStatus === "inactive" ? "selected" : ""}>Inactive</option>
        </select></label>
        <label class="network-note"><span>Reason / notes</span><input type="text" value="${escapeHtml(change.notes)}" data-network-notes></label>
        <button class="row-remove" type="button" data-remove-network="${index}" aria-label="Remove airport change ${index + 1}">Remove</button>
      </div>`).join("")
    : '<p class="setup-empty">No network changes. The baseline city roster remains unchanged.</p>';

  renderSetupPreflight();
}

function readSetupForm() {
  const fleetCounts = {};
  $("[data-setup-fleet-row]").forEach((row) => {
    const fleet = row.querySelector("[data-setup-fleet-name]").value.trim().toUpperCase();
    if (fleet) fleetCounts[fleet] = Number(row.querySelector("[data-setup-fleet-count]").value);
  });
  const kind = $("#setup-start-kind").value;
  const value = {
    ...state.buildConfig,
    schedule: {
      number: Number($("#setup-number").value),
      version: $("#setup-version").value,
      label: $("#setup-label").value,
      mode: $("#setup-mode").value,
      status: "draft",
    },
    startingPoint: {
      kind,
      scheduleId: kind === "blank" ? null : $("#setup-baseline").value,
    },
    fleetCounts,
    connectionWindowMinutes: {
      minimum: Number($("#setup-connect-min").value),
      maximum: Number($("#setup-connect-max").value),
    },
    inputs: {
      instructions: {
        version: $("#setup-instruction-version").value,
        source: $("#setup-instruction-source").value,
      },
      cityInformation: {
        filename: $("#setup-city-file").value,
        sha256: $("#setup-city-sha").value,
      },
      operatingPolicy: {
        filename: $("#setup-policy-file").value,
        sha256: $("#setup-policy-sha").value,
      },
      demandData: {
        version: $("#setup-demand-version").value,
      },
    },
    networkChanges: $("[data-setup-network-row]").map((row) => ({
      airport: row.querySelector("[data-network-airport]").value,
      action: row.querySelector("[data-network-action]").value,
      targetStatus: row.querySelector("[data-network-status]").value,
      notes: row.querySelector("[data-network-notes]").value,
    })),
    notes: $("#setup-notes").value,
  };
  state.buildConfig = normalizeBuildConfig(value);
  state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
}

function updateSetupDraft(message = "Draft saved") {
  readSetupForm();
  $("#setup-baseline").disabled = state.buildConfig.startingPoint.kind === "blank";
  saveSetupDraft(message);
  renderSetupPreflight();
}

function renderSetupPreflight() {
  const report = state.buildPreflight || validateBuildConfig(state.buildConfig, state.canonical);
  state.buildPreflight = report;
  $("#preflight-summary").textContent = report.status === "pass"
    ? `Ready · ${report.summary.warnings} warning${report.summary.warnings === 1 ? "" : "s"}`
    : `${report.summary.blocking} blocking`;
  $("#preflight-summary").classList.toggle("is-blocking", report.status === "fail");
  $("#preflight-list").innerHTML = report.checks.map((item) => `<article class="preflight-item status-${escapeHtml(item.status)}">
    <span class="preflight-mark" aria-hidden="true">${item.status === "pass" ? "✓" : item.status === "warning" ? "!" : "×"}</span>
    <div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.message)}</p></div>
    <span class="preflight-status">${escapeHtml(statusLabel(item.status))}</span>
  </article>`).join("");
}

function addFleetType() {
  readSetupForm();
  let candidate = "NEW_TYPE";
  let suffix = 2;
  while (Object.hasOwn(state.buildConfig.fleetCounts, candidate)) {
    candidate = `NEW_TYPE_${suffix}`;
    suffix += 1;
  }
  state.buildConfig.fleetCounts[candidate] = 0;
  state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
  saveSetupDraft();
  renderSetup();
  const inputs = $("[data-setup-fleet-name]");
  inputs.at(-1)?.select();
}

function addNetworkChange() {
  readSetupForm();
  state.buildConfig.networkChanges.push({
    airport: "",
    action: "add",
    targetStatus: "destination",
    notes: "",
  });
  state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
  saveSetupDraft();
  renderSetup();
  $("[data-network-airport]").at(-1)?.focus();
}

function exportSetupConfig() {
  updateSetupDraft("Draft exported");
  const blob = new Blob([serializeBuildConfig(state.buildConfig)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = buildConfigFilename(state.buildConfig);
  anchor.click();
  URL.revokeObjectURL(url);
}

async function importSetupConfig(file) {
  if (!file) return;
  try {
    const imported = normalizeBuildConfig(JSON.parse(await file.text()));
    state.buildConfig = imported;
    state.buildPreflight = validateBuildConfig(imported, state.canonical);
    saveSetupDraft("Imported and saved");
    renderSetup();
  } catch (error) {
    $("#setup-status").textContent = "Import failed";
    window.alert(`Could not import build configuration: ${error.message}`);
  } finally {
    $("#setup-import-file").value = "";
  }
}

function handleReference(button) {
  const type = button.dataset.refType;
  const value = button.dataset.ref;
  if (type === "city") {
    $("#gate-airport").value = value;
    renderGates();
    activateTab("gates");
    return;
  }
  $("#routing-line").value = "";
  $("#routing-origin").value = "";
  $("#routing-destination").value = "";
  if (type === "fleet") {
    $("#routing-search").value = "";
    $("#routing-fleet").value = value;
  } else {
    $("#routing-search").value = `${type}:${value}`;
    $("#routing-fleet").value = "";
  }
  state.routingPage = 1;
  renderRoutings();
  activateTab("routings");
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const removeFleet = event.target.closest("[data-remove-fleet]");
    if (removeFleet) {
      readSetupForm();
      const fleet = Object.keys(state.buildConfig.fleetCounts)[Number(removeFleet.dataset.removeFleet)];
      delete state.buildConfig.fleetCounts[fleet];
      state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
      saveSetupDraft();
      renderSetup();
      return;
    }
    const removeNetwork = event.target.closest("[data-remove-network]");
    if (removeNetwork) {
      readSetupForm();
      state.buildConfig.networkChanges.splice(Number(removeNetwork.dataset.removeNetwork), 1);
      state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
      saveSetupDraft();
      renderSetup();
      return;
    }
    const instruction = event.target.closest("[data-instruction-id]");
    if (instruction) {
      event.preventDefault();
      event.stopPropagation();
      openInstruction(instruction.dataset.instructionId);
      return;
    }
    const closeClaim = event.target.closest("#claim-tooltip-close");
    if (closeClaim) {
      closeGateClaimDetails();
      return;
    }
    const gateClaim = event.target.closest("[data-gate-claim]");
    if (gateClaim) {
      toggleGateClaimDetails(gateClaim);
      return;
    }
    const tab = event.target.closest("[data-tab]");
    if (tab) activateTab(tab.dataset.tab);
    const openTab = event.target.closest("[data-open-tab]");
    if (openTab) activateTab(openTab.dataset.openTab);
    const openCheck = event.target.closest("[data-open-check]");
    if (openCheck) {
      activateTab("validation");
      renderValidation(openCheck.dataset.openCheck);
    }
    const reference = event.target.closest("[data-ref-type]");
    if (reference) handleReference(reference);
    const page = event.target.closest("[data-page-context]");
    if (page && !page.disabled) {
      const value = Number(page.dataset.page);
      if (page.dataset.pageContext === "routing") {
        state.routingPage = value;
        renderRoutings();
      } else if (page.dataset.pageContext === "planning") {
        state.planningPage = value;
        renderPlanning();
      } else {
        state.timetablePage = value;
        renderTimetable();
      }
    }
  });

  $("#schedule-select").addEventListener("change", async (event) => {
    $("#app").hidden = true;
    $("#loading-state").hidden = false;
    try {
      await loadSchedule(event.target.value);
      $("#loading-state").hidden = true;
      $("#app").hidden = false;
    } catch (error) {
      $("#loading-state").hidden = true;
      $("#error-message").textContent = error.message;
      $("#error-state").hidden = false;
    }
  });

  $("#setup-form").addEventListener("input", () => updateSetupDraft());
  $("#setup-form").addEventListener("change", () => updateSetupDraft());
  $("#setup-add-fleet").addEventListener("click", addFleetType);
  $("#setup-add-network").addEventListener("click", addNetworkChange);
  $("#setup-save").addEventListener("click", () => updateSetupDraft("Saved in this browser"));
  $("#setup-export").addEventListener("click", exportSetupConfig);
  $("#setup-import").addEventListener("click", () => $("#setup-import-file").click());
  $("#setup-import-file").addEventListener("change", (event) => importSetupConfig(event.target.files[0]));
  $("#setup-reset").addEventListener("click", () => {
    if (!window.confirm("Reset this browser draft to a new configuration copied from the selected baseline?")) return;
    state.buildConfig = createBuildConfig(state.canonical, state.manifest);
    state.buildPreflight = validateBuildConfig(state.buildConfig, state.canonical);
    saveSetupDraft("Draft reset");
    renderSetup();
  });

  $("#routing-search").addEventListener("input", () => { state.routingPage = 1; renderRoutings(); });
  ["#routing-fleet", "#routing-line", "#routing-origin", "#routing-destination"].forEach((selector) => {
    $(selector).addEventListener("change", () => { state.routingPage = 1; renderRoutings(); });
  });
  $("#routing-page-size").addEventListener("change", (event) => {
    state.routingPageSize = event.target.value === "all" ? "all" : Number(event.target.value);
    state.routingPage = 1;
    renderRoutings();
  });
  ["#planning-fleet", "#planning-origin", "#planning-destination"].forEach((selector) => {
    $(selector).addEventListener("change", () => { state.planningPage = 1; renderPlanning(); });
  });
  $("#validation-search").addEventListener("input", () => renderValidation());
  $("#validation-status").addEventListener("change", () => renderValidation());
  $("#instruction-search").addEventListener("input", () => renderInstructions());
  $("#instruction-kind").addEventListener("change", () => renderInstructions());
  ["#timetable-search", "#timetable-origin", "#timetable-destination", "#timetable-fleet", "#timetable-connections"].forEach((selector) => {
    $(selector).addEventListener(selector === "#timetable-search" ? "input" : "change", () => { state.timetablePage = 1; renderTimetable(); });
  });
  $("#gate-airport").addEventListener("change", renderGates);
  $("#retry-button").addEventListener("click", () => location.reload());
  window.addEventListener("hashchange", () => activateTab(location.hash.slice(1), false));
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  bindEvents();
  initialize();
}
