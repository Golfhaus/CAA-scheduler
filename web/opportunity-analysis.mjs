const DAY = 1440;
const rad = (n) => Number(n) * Math.PI / 180;
const wait = (a, b) => ((Number(b) - Number(a)) % DAY + DAY) % DAY;
const clock = (n) => `${String(Math.floor(((n % DAY) + DAY) % DAY / 60)).padStart(2, "0")}:${String(((n % DAY) + DAY) % DAY % 60).padStart(2, "0")}`;

export function parseAirportDemand(text) {
  const rows = []; let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') { if (quoted && text[i + 1] === '"') { cell += '"'; i++; } else quoted = !quoted; }
    else if (!quoted && (ch === ',' || ch === '\n')) { row.push(cell.replace(/\r$/, "")); cell = ""; if (ch === '\n') { rows.push(row); row = []; } }
    else cell += ch;
  }
  if (quoted) throw new Error("Demand CSV has an unfinished quoted field.");
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const header = rows.findIndex((r) => r[0]?.trim() === 'Origin \\ Dest');
  if (header < 0) throw new Error("Airport demand matrix header is missing.");
  const codes = rows[header].slice(1).map((v) => v.trim());
  if (new Set(codes).size !== codes.length) throw new Error("Demand matrix contains duplicate airports.");
  const values = {};
  for (const r of rows.slice(header + 1).filter((r) => r[0]?.trim())) {
    const origin = r[0].trim();
    if (values[origin] || r.length !== codes.length + 1) throw new Error("Demand matrix rows do not match its header.");
    values[origin] = {};
    codes.forEach((destination, i) => {
      const raw = r[i + 1].trim(); const number = Number(raw);
      if ((!raw && origin !== destination) || !Number.isFinite(number) || number < 0) throw new Error(`Missing or invalid demand: ${origin} to ${destination}.`);
      values[origin][destination] = number;
    });
  }
  if (codes.some((c) => !values[c]) || Object.keys(values).length !== codes.length) throw new Error("Demand matrix origins and destinations differ.");
  return values;
}

export function buildServiceAnalysis(canonical, demand, enumerate) {
  const cities = new Map(canonical.cities.filter((c) => c.active).map((c) => [c.code, c]));
  const hubs = new Set([...canonical.operatingPolicy.hubs, ...canonical.operatingPolicy.focusCities]);
  const timezone = Object.fromEntries([...cities].map(([code, c]) => [code, c.timezone]));
  const minimum = canonical.schedule.connectionWindowMinutes.minimum;
  const maximum = canonical.schedule.connectionWindowMinutes.maximum;
  const flights = canonical.legs.map((l) => ({origin: l.origin, dest: l.destination, dep: l.departure, arr: l.arrival, flight: l.flight, fleet: l.fleet}));
  const timetable = {flights, minConnect: minimum, maxConnect: maximum};
  const distanceCache = new Map();
  const distance = (a, b) => {
    const key = `${a}-${b}`; if (distanceCache.has(key)) return distanceCache.get(key);
    const x = cities.get(a), y = cities.get(b);
    if (!x || !y || [x.latitude, x.longitude, y.latitude, y.longitude].some((v) => v == null || !Number.isFinite(Number(v)))) return null;
    const h = Math.sin(rad(y.latitude - x.latitude) / 2) ** 2 + Math.cos(rad(x.latitude)) * Math.cos(rad(y.latitude)) * Math.sin(rad(y.longitude - x.longitude) / 2) ** 2;
    const n = 3440.065 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h))); distanceCache.set(key, n); return n;
  };
  const records = new Map(), paths = new Map(), direct = new Map();
  canonical.legs.forEach((l) => { const key = `${l.origin}-${l.destination}`; if (!direct.has(key)) direct.set(key, []); direct.get(key).push(l); });
  for (const origin of cities.keys()) {
    for (const destination of cities.keys()) if (origin !== destination) {
      const key = `${origin}-${destination}`;
      records.set(key, {key, origin, destination, demand: demand?.[origin]?.[destination] ?? null, counts: [0, 0, 0], reasonableCounts: [0, 0, 0], best: [null, null, null], reasonableBest: [null, null, null]});
    }
    for (const option of enumerate(timetable, origin, hubs, timezone)) {
      const record = records.get(`${origin}-${option.dest}`); if (!record) continue;
      const straight = distance(origin, option.dest); const segments = option.legs.map((l) => distance(l.origin, l.dest));
      const circuity = straight > 0 && segments.every((v) => v != null) ? segments.reduce((a, b) => a + b, 0) / straight : null;
      const reasonable = option.stops === 0 || (circuity != null && circuity <= 2.25 + 1e-10);
      record.counts[option.stops]++;
      if (!record.best[option.stops] || option.totalMinutes < record.best[option.stops].totalMinutes) record.best[option.stops] = {...option, circuity};
      if (reasonable) {
        record.reasonableCounts[option.stops]++;
        if (!record.reasonableBest[option.stops] || option.totalMinutes < record.reasonableBest[option.stops].totalMinutes) record.reasonableBest[option.stops] = {...option, circuity};
      }
      paths.set(option.legs.map((l) => l.flight).join("-"), {market: record.key, stops: option.stops, minutes: option.totalMinutes, reasonable});
    }
  }
  const nearMisses = [];
  for (const record of records.values()) {
    record.sharedHubs = [...hubs].filter((h) => direct.has(`${record.origin}-${h}`) && direct.has(`${h}-${record.destination}`));
    if (record.counts[0] || record.reasonableCounts[1]) continue;
    let closest = null;
    for (const hub of record.sharedHubs) {
      const d = distance(record.origin, record.destination), a = distance(record.origin, hub), b = distance(hub, record.destination);
      if (!(d > 0 && a != null && b != null && (a + b) / d <= 2.25 + 1e-10)) continue;
      for (const first of direct.get(`${record.origin}-${hub}`)) for (const second of direct.get(`${hub}-${record.destination}`)) {
        const transfer = wait(first.arrivalMinute, second.departureMinute);
        if (transfer >= minimum && transfer <= maximum) continue;
        const delta = [minimum - transfer, maximum - transfer, DAY + minimum - transfer].sort((x, y) => Math.abs(x) - Math.abs(y))[0];
        const candidate = {market: record.key, origin: record.origin, destination: record.destination, demand: record.demand, hub, first, second, transfer, delta, adjustment: Math.abs(delta), gapCurrent: !record.counts[0] && !record.counts[1]};
        if (!closest || candidate.adjustment < closest.adjustment || (candidate.adjustment === closest.adjustment && first.flight < closest.first.flight)) closest = candidate;
      }
    }
    if (closest) {
      closest.options = [{flight: closest.second.flight, shift: closest.delta}, {flight: closest.first.flight, shift: -closest.delta}].map((o) => ({...o, screen: screenTimingChange(canonical, o.flight, o.shift)}));
      closest.preferred = closest.options.find((o) => !o.screen.issues.length) || closest.options[0];
      nearMisses.push(closest);
    }
  }
  nearMisses.sort((a, b) => (b.demand ?? -1) - (a.demand ?? -1) || a.adjustment - b.adjustment || a.market.localeCompare(b.market));
  const pairs = [];
  for (const a of cities.keys()) for (const b of cities.keys()) if (a < b) pairs.push({key: `${a}-${b}`, a, b, forward: records.get(`${a}-${b}`), reverse: records.get(`${b}-${a}`)});
  return {canonical, cities, hubs, minimum, maximum, records, paths, pairs, nearMisses, distance};
}

export function coverageView(record, geographic = false) {
  const counts = geographic ? record.reasonableCounts : record.counts;
  const best = geographic ? record.reasonableBest : record.best;
  const stops = counts.findIndex((n) => n > 0);
  return {stops: stops < 0 ? null : stops, gap: !counts[0] && !counts[1], counts, best, fastest: best.filter(Boolean).sort((a, b) => a.totalMinutes - b.totalMinutes)[0] || null};
}

export function screenTimingChange(canonical, flight, shift) {
  const leg = canonical.legs.find((l) => Number(l.flight) === Number(flight));
  if (!leg || !Number.isFinite(shift)) throw new Error("Unknown flight or invalid timing adjustment.");
  const route = canonical.legs.filter((l) => l.route === leg.route).sort((a, b) => a.sequenceWithinRoute - b.sequenceWithinRoute);
  const index = route.indexOf(leg), issues = [], turns = [];
  const minimum = canonical.operatingPolicy.turns.minimumMinutes;
  if (index > 0) turns.push({side: "Before flight", minutes: wait(route[index - 1].arrivalMinute, leg.departureMinute) + shift});
  if (index < route.length - 1) turns.push({side: "After flight", minutes: wait(leg.arrivalMinute, route[index + 1].departureMinute) - shift});
  if (!index || index === route.length - 1) {
    const line = canonical.legs.filter((l) => l.line === leg.line); const days = [...new Set(line.map((l) => l.day))].sort((a, b) => a - b), at = days.indexOf(leg.day);
    if (!index) { const previous = line.filter((l) => l.day === days[(at + days.length - 1) % days.length]).sort((a, b) => a.sequenceWithinRoute - b.sequenceWithinRoute).at(-1); if (previous) turns.push({side: "Prior overnight", minutes: wait(previous.arrivalMinute, leg.departureMinute) + shift}); }
    if (index === route.length - 1) { const next = line.filter((l) => l.day === days[(at + 1) % days.length]).sort((a, b) => a.sequenceWithinRoute - b.sequenceWithinRoute)[0]; if (next) turns.push({side: "Next overnight", minutes: wait(leg.arrivalMinute, next.departureMinute) - shift}); }
  }
  turns.filter((t) => t.minutes < minimum).forEach((t) => issues.push(`${t.side}: ${t.minutes} min, below ${minimum} min`));
  const dep = leg.departureMinute + shift, arr = leg.arrivalMinute + shift;
  const windows = canonical.operatingPolicy.departureWindows, hubs = new Set([...canonical.operatingPolicy.hubs, ...canonical.operatingPolicy.focusCities]);
  const latest = hubs.has(leg.origin) ? windows.hubOrFocusLatestMinute : windows.destinationLatestMinute;
  const minute = ((dep % DAY) + DAY) % DAY;
  const arrival = ((arr % DAY) + DAY) % DAY;
  const redEye = (minute > windows.destinationLatestMinute || minute <= windows.redEyeLatestMinute) && arrival >= windows.redEyeArrivalMinimumMinute && arrival <= windows.redEyeArrivalMaximumMinute;
  if ((minute < windows.earliestMinute || minute > latest) && !redEye) issues.push("Departure outside the operating window");
  if (dep < 180 && leg.departureMinute >= 180 || dep >= 180 && leg.departureMinute < 180) issues.push("Crosses the 03:00 operating-day boundary");
  for (const assignment of canonical.bankAssignments || []) if (assignment.legId === leg.id) {
    const bank = canonical.hubBanks.find((b) => b.id === assignment.bankId);
    const touch = assignment.operation === "arrival" ? arr : dep;
    if (bank && wait(bank.startMinute, touch) >= wait(bank.startMinute, bank.endMinute)) issues.push(`${assignment.operation} outside assigned ${bank.id}`);
  }
  const peers = canonical.legs.filter((l) => l.id !== leg.id && l.origin === leg.origin && l.destination === leg.destination);
  if (peers.some((l) => Math.min(wait(l.departureMinute, dep), wait(dep, l.departureMinute)) < canonical.operatingPolicy.section26.hardFloorMinutes)) issues.push("Same-market departures violate the spacing hard floor");
  return {leg, shift, departure: clock(dep), arrival: clock(arr), turns, issues};
}

export function compareServiceAnalyses(before, after, geographic = false) {
  const lostPaths = [...before.paths].filter(([key, p]) => (!geographic || p.reasonable) && (!after.paths.has(key) || geographic && !after.paths.get(key).reasonable)).length;
  const result = {lostPaths, gained: [], lost: [], faster: [], slower: []};
  for (const [key, old] of before.records) {
    const now = after.records.get(key); if (!now) continue;
    const a = coverageView(old, geographic), b = coverageView(now, geographic);
    const row = {market: key, origin: old.origin, destination: old.destination, demand: old.demand, beforeMinutes: a.fastest?.totalMinutes ?? null, afterMinutes: b.fastest?.totalMinutes ?? null};
    if (a.gap && !b.gap) result.gained.push(row);
    if (!a.gap && b.gap) result.lost.push(row);
    if (a.fastest && b.fastest && b.fastest.totalMinutes < a.fastest.totalMinutes) result.faster.push(row);
    if (a.fastest && b.fastest && b.fastest.totalMinutes > a.fastest.totalMinutes) result.slower.push(row);
  }
  for (const key of ["gained", "lost", "faster", "slower"]) result[key].sort((a, b) => (b.demand ?? -1) - (a.demand ?? -1));
  return result;
}

export function buildBankEffectiveness(analysis, hub, bankId = "all") {
  const {canonical, hubs, minimum, maximum, distance} = analysis;
  const allArrivals = canonical.legs.filter((l) => l.destination === hub), allDepartures = canonical.legs.filter((l) => l.origin === hub);
  const assignment = new Map((canonical.bankAssignments || []).map((a) => [`${a.legId}:${a.operation}`, a.bankId]));
  const included = (leg, op) => bankId === "all" || (bankId === "unassigned" ? !assignment.has(`${leg.id}:${op}`) : assignment.get(`${leg.id}:${op}`) === bankId);
  const arrivals = allArrivals.filter((l) => included(l, "arrival")), departures = allDepartures.filter((l) => included(l, "departure"));
  const marketKeys = new Set();
  const connections = (first, second) => {
    if (first.origin === second.destination) return null;
    const transfer = wait(first.arrivalMinute, second.departureMinute);
    if (transfer < minimum || transfer > maximum) return null;
    const straight = distance(first.origin, second.destination), a = distance(first.origin, hub), b = distance(hub, second.destination);
    if (!(straight > 0 && a != null && b != null && (a + b) / straight <= 2.25 + 1e-10)) return null;
    const key = `${first.origin}-${second.destination}`;
    return {key, first, second, wait: transfer, demand: analysis.records.get(key)?.demand ?? null};
  };
  const inbound = arrivals.map((leg) => ({leg, choices: allDepartures.map((next) => connections(leg, next)).filter(Boolean)}));
  const outbound = departures.map((leg) => ({leg, choices: allArrivals.map((previous) => connections(previous, leg)).filter(Boolean)}));
  [...inbound, ...outbound].forEach((r) => r.choices.forEach((c) => marketKeys.add(c.key)));
  const markets = [...marketKeys].map((key) => analysis.records.get(key));
  const matrix = arrivals.map((first) => departures.map((second) => {
    const transfer = wait(first.arrivalMinute, second.departureMinute), connection = connections(first, second);
    return {first, second, transfer, connection, reason: first.origin === second.destination ? "Return to origin" : transfer < minimum || transfer > maximum ? "Outside connection window" : "Excessive or unknown detour"};
  }));
  return {hub, bankId, arrivals, departures, inbound, outbound, markets, matrix, inboundWithoutConnections: inbound.filter((r) => !r.choices.length).length, outboundWithoutFeed: outbound.filter((r) => !r.choices.length).length, uniqueDemand: markets.every((r) => r.demand != null) ? markets.reduce((s, r) => s + r.demand, 0) : null};
}
