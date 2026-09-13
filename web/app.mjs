const PAGE_SIZE = 50;

const state = {
  manifest: null,
  scheduleEntry: null,
  canonical: null,
  structural: null,
  operating: null,
  timetable: null,
  gates: null,
  routingPage: 1,
  timetablePage: 1,
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

export function legMatches(leg, query, fleet = "") {
  if (fleet && leg.fleet !== fleet) return false;
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

export function splitClaimSegments(start, end) {
  const duration = Math.max(0, Number(end) - Number(start));
  if (duration >= 1440) return [{ start: 0, duration: 1440 }];
  const normalized = ((Number(start) % 1440) + 1440) % 1440;
  if (normalized + duration <= 1440) return [{ start: normalized, duration }];
  return [
    { start: normalized, duration: 1440 - normalized },
    { start: 0, duration: normalized + duration - 1440 },
  ];
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
  const valid = ["overview", "routings", "validation", "timetable", "gates"];
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
    timetable: data.timetable,
    gates: data.gates,
    routingPage: 1,
    timetablePage: 1,
  });
  renderAll();
}

async function initialize() {
  try {
    state.manifest = await fetchJson("schedules.json");
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
  renderOverview();
  populateFilters();
  renderRoutings();
  renderValidation();
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
  populateSelect($("#routing-fleet"), fleets, "All fleets");
  populateSelect($("#timetable-fleet"), fleets, "All fleets");
  populateSelect($("#timetable-origin"), cities, "Any origin");
  populateSelect($("#timetable-destination"), cities, "Any destination");

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

function paginate(items, page) {
  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), pageCount);
  return {
    page: safePage,
    pageCount,
    rows: items.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
  };
}

function renderPagination(container, context, total, page, pageCount) {
  const start = total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const end = Math.min(total, page * PAGE_SIZE);
  container.innerHTML = `<span>Showing ${start.toLocaleString()}–${end.toLocaleString()} of ${total.toLocaleString()}</span><div class="pagination-buttons"><button type="button" data-page-context="${context}" data-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>Previous</button><button type="button" data-page-context="${context}" data-page="${page + 1}" ${page >= pageCount ? "disabled" : ""}>Next</button></div>`;
}

function renderRoutings() {
  const query = $("#routing-search").value;
  const fleet = $("#routing-fleet").value;
  const filtered = state.canonical.legs.filter((leg) => legMatches(leg, query, fleet));
  const paged = paginate(filtered, state.routingPage);
  state.routingPage = paged.page;
  $("#routing-result-count").textContent = `${filtered.length.toLocaleString()} flights`;
  $("#routing-rows").innerHTML = paged.rows.length
    ? paged.rows.map((leg) => `<tr id="flight-${leg.flight}"><td class="route-number">${leg.route}</td><td><strong>${escapeHtml(leg.line)}</strong> / ${leg.day}</td><td>${leg.sequenceWithinRoute}</td><td class="flight-number">${leg.flight}</td><td><strong>${escapeHtml(leg.origin)}</strong><span class="market-arrow">→</span><strong>${escapeHtml(leg.destination)}</strong></td><td>${escapeHtml(leg.departure)}–${escapeHtml(leg.arrival)}</td><td><span class="fleet-badge">${escapeHtml(leg.fleet)}</span></td></tr>`).join("")
    : `<tr class="empty-row"><td colspan="7">No routings match these filters.</td></tr>`;
  renderPagination($("#routing-pagination"), "routing", filtered.length, paged.page, paged.pageCount);
}

function timetableMatches(flight) {
  const query = $("#timetable-search").value.trim().toLowerCase();
  return (!query || [flight.flight, flight.origin, flight.dest, flight.fleet].some((value) => String(value).toLowerCase().includes(query)))
    && (!$("#timetable-origin").value || flight.origin === $("#timetable-origin").value)
    && (!$("#timetable-destination").value || flight.dest === $("#timetable-destination").value)
    && (!$("#timetable-fleet").value || flight.fleet === $("#timetable-fleet").value);
}

function renderTimetable() {
  const filtered = state.timetable.flights.filter(timetableMatches);
  const paged = paginate(filtered, state.timetablePage);
  state.timetablePage = paged.page;
  $("#connection-window").textContent = `${state.timetable.minConnect}–${state.timetable.maxConnect} minute connection window`;
  $("#timetable-result-count").textContent = `${filtered.length.toLocaleString()} flights`;
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
  return `<details class="check-card status-${check.status}" id="check-${escapeHtml(check.id)}" ${forceOpen ? "open" : ""}><summary><span class="check-title"><strong>${escapeHtml(check.title)}</strong><span>${escapeHtml(check.section)} · ${effectiveCount} effective findings</span></span><span class="check-badges">${check.hardStop ? '<span class="hard-stop-badge">Hard stop</span>' : ""}<span class="check-status">${escapeHtml(statusLabel(check.status))}</span></span></summary><div class="check-body"><p class="check-message">${escapeHtml(check.message)}</p>${findings}</div></details>`;
}

function renderGates() {
  const code = $("#gate-airport").value;
  const city = state.gates.cities.find((item) => item.code === code) || state.gates.cities[0];
  if (!city) return;
  const gateClaims = city.claims.filter((claim) => claim.rowType === "gate");
  const standClaims = city.claims.filter((claim) => claim.rowType === "stand");
  $("#gate-metrics").innerHTML = [
    metricCard("Airport", city.code, city.name),
    metricCard("Peak use", city.peakUsed, "Simultaneous aircraft", city.peakUsed > city.nGates + city.nStands ? "is-danger" : ""),
    metricCard("Gates", city.nGates, `${gateClaims.length} assigned claim pieces`),
    metricCard("Stands", city.nStands, `${standClaims.length} assigned claim pieces`),
  ].join("");
  const colors = state.gates.fleetColors;
  $("#timeline-key").innerHTML = Object.entries(colors).map(([fleet, color]) => `<span class="legend-item"><i class="legend-swatch" style="background:${escapeHtml(color)}"></i>${escapeHtml(fleet)}</span>`).join("");

  const maximumGateRow = Math.max(city.nGates, ...gateClaims.map((claim) => claim.row));
  const maximumStandRow = Math.max(city.nStands, ...standClaims.map((claim) => claim.row));
  const lanes = [
    ...Array.from({ length: maximumGateRow }, (_, index) => ({ type: "gate", row: index + 1 })),
    ...Array.from({ length: maximumStandRow }, (_, index) => ({ type: "stand", row: index + 1 })),
  ];
  const axis = [0, 240, 480, 720, 960, 1200, 1440];
  $("#gate-timeline").innerHTML = `<div class="time-axis"><span></span><div class="axis-track">${axis.map((minute) => `<span class="axis-label" style="left:${(minute / 1440) * 100}%">${formatMinute(minute)}</span>`).join("")}</div></div>${lanes.map((lane) => renderLane(city, lane, colors)).join("")}`;
}

function renderLane(city, lane, colors) {
  const claims = city.claims.filter((claim) => claim.rowType === lane.type && claim.row === lane.row);
  const bars = claims.flatMap((claim) => splitClaimSegments(claim.start, claim.end).map((segment) => `<span class="claim-bar kind-${lane.type}" title="${escapeHtml(`${claim.label} · ${claim.fleet} · ${claim.kind} · ${formatMinute(claim.start)}–${formatMinute(claim.end)}`)}" style="left:${(segment.start / 1440) * 100}%;width:${Math.max(0.12, (segment.duration / 1440) * 100)}%;background:${escapeHtml(colors[claim.fleet] || "#cbd5e1")}">${escapeHtml(claim.label)}</span>`)).join("");
  return `<div class="timeline-row"><span class="lane-label">${lane.type === "gate" ? "Gate" : "Stand"} ${lane.row}</span><div class="lane-track">${bars}</div></div>`;
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

  $("#routing-search").addEventListener("input", () => { state.routingPage = 1; renderRoutings(); });
  $("#routing-fleet").addEventListener("change", () => { state.routingPage = 1; renderRoutings(); });
  $("#validation-search").addEventListener("input", () => renderValidation());
  $("#validation-status").addEventListener("change", () => renderValidation());
  ["#timetable-search", "#timetable-origin", "#timetable-destination", "#timetable-fleet"].forEach((selector) => {
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
