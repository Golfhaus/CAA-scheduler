const DAY = 1440;
const OFFSETS = {Eastern: -300, Central: -360, Mountain: -420};
const ZONES = {Eastern: "ET", Central: "CT", Mountain: "MT"};
const clock = (minute) => {
  const normalized = ((minute % DAY) + DAY) % DAY;
  return `${String(Math.floor(normalized / 60)).padStart(2, "0")}:${String(normalized % 60).padStart(2, "0")}`;
};
const dayLabel = (minute) => {
  const day = Math.floor(minute / DAY);
  return day ? ` (${day > 0 ? "+" : ""}${day} day${Math.abs(day) === 1 ? "" : "s"})` : "";
};

export function routingDetailOptions(canonical) {
  const routes = new Map();
  (canonical?.legs || []).forEach((leg) => {
    const id = String(leg.route);
    if (!routes.has(id)) routes.set(id, {id, route: leg.route, line: leg.line, day: leg.day, fleet: leg.fleet});
  });
  return [...routes.values()].sort((a, b) => Number(a.route) - Number(b.route));
}

// A single airport's time zone is used for geometry. Flight tooltips retain
// local endpoint clocks; gate claims are converted from their airport's zone.
export function buildRoutingDetails(canonical, gates, route) {
  const legs = (canonical?.legs || []).filter((leg) => String(leg.route) === String(route))
    .sort((a, b) => Number(a.sequenceWithinRoute) - Number(b.sequenceWithinRoute));
  if (!legs.length) return null;
  const cities = new Map(canonical.cities.map((city) => [city.code, city]));
  const first = legs[0];
  const reference = cities.get(first.origin);
  const offset = (code) => OFFSETS[cities.get(code)?.timezone] ?? 0;
  const referenceOffset = offset(first.origin);
  const localTime = (minute, code) => `${clock(minute)} ${ZONES[cities.get(code)?.timezone] || "local"}${dayLabel(minute)}`;
  const cityName = (code) => `${code} — ${cities.get(code)?.displayName || cities.get(code)?.name || code}`;
  let previousArrival = -Infinity;
  const flights = legs.map((leg) => {
    let start = Number(leg.departureMinute) + referenceOffset - offset(leg.origin);
    while (start < previousArrival) start += DAY;
    let end = Number(leg.arrivalMinute) + referenceOffset - offset(leg.destination);
    while (end <= start) end += DAY;
    previousArrival = end;
    const departure = start - referenceOffset + offset(leg.origin);
    const arrival = end - referenceOffset + offset(leg.destination);
    return {kind: "inflight", start, end, leg, label: String(leg.flight),
      title: `Flight ${leg.flight} · ${leg.origin} → ${leg.destination}`,
      detail: `${cityName(leg.origin)} ${localTime(departure, leg.origin)} → ${cityName(leg.destination)} ${localTime(arrival, leg.destination)}`};
  });
  const start = Math.min(180, Math.floor(flights[0].start / 60) * 60);
  const end = Math.max(1620, Math.ceil(flights.at(-1).end / 60) * 60);
  const groundWindows = [
    {role: "originator", city: first.origin, start, end: flights[0].start},
    ...flights.slice(0, -1).map((flight, index) => ({role: "turn", city: flight.leg.destination, start: flight.end, end: flights[index + 1].start})),
    {role: "terminator", city: legs.at(-1).destination, start: flights.at(-1).end, end},
  ];
  const ground = [];
  let unassigned = 0;
  for (const city of gates?.cities || []) {
    for (const claim of city.claims || []) {
      const identities = String(claim.label).split(/\s*(?:->|→)\s*/);
      let role;
      if (identities.length === 1 && identities[0] === String(route)) role = "turn";
      else if (identities[0] === String(route)) role = "terminator";
      else if (identities.at(-1) === String(route)) role = "originator";
      else continue;
      const rawStart = Number(claim.start) + referenceOffset - offset(city.code);
      const rawEnd = Number(claim.end) + referenceOffset - offset(city.code);
      for (const window of groundWindows.filter((window) => window.role === role && window.city === city.code)) {
        // Align the prior-day originator RON and following-day terminator RON
        // against the selected route, rather than repeating them at both ends.
        const firstShift = Math.floor((window.start - rawEnd) / DAY) + 1;
        const lastShift = Math.ceil((window.end - rawStart) / DAY) - 1;
        for (let shift = firstShift; shift <= lastShift; shift++) {
          const left = Math.max(window.start, rawStart + shift * DAY);
          const right = Math.min(window.end, rawEnd + shift * DAY);
          if (right <= left) continue;
          if (!["gate", "stand"].includes(claim.rowType)) { unassigned++; continue; }
          const position = `${claim.rowType === "gate" ? "Gate" : "Stand"} ${claim.row}`;
          const localStart = left - referenceOffset + offset(city.code);
          const localEnd = right - referenceOffset + offset(city.code);
          ground.push({kind: claim.rowType, start: left, end: right, city: city.code,
            row: claim.row, role, claim, label: `${city.code} ${claim.row}`,
            title: `${cityName(city.code)} · ${position}`,
            detail: `${localTime(localStart, city.code)}–${localTime(localEnd, city.code)} · ${role === "turn" ? "Turn / ground hold" : role === "originator" ? "Before originator" : "After terminator"}`});
        }
      }
    }
  }
  const blocks = [...flights, ...ground].sort((a, b) => a.start - b.start || a.end - b.end);
  return {route: first.route, line: first.line, day: first.day, fleet: first.fleet,
    referenceCity: first.origin, timezone: reference?.timezone || "local",
    zone: ZONES[reference?.timezone] || "local", start, end, blocks, flights,
    unassigned, blockMinutes: flights.reduce((sum, flight) => sum + flight.end - flight.start, 0)};
}
