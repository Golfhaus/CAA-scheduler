const DAY_MINUTES = 1440;
const operatingMinute = (minute) => ((Number(minute) - 180) % DAY_MINUTES + DAY_MINUTES) % DAY_MINUTES;

function insideWindow(minute, bank) {
  const offset = ((Number(minute) - bank.startMinute) % DAY_MINUTES + DAY_MINUTES) % DAY_MINUTES;
  const width = ((bank.endMinute - bank.startMinute) % DAY_MINUTES + DAY_MINUTES) % DAY_MINUTES;
  return offset < width;
}

export function bankBreakdownAirports(canonical) {
  const hubs = new Set(canonical.operatingPolicy.hubs);
  const focusCities = new Set(canonical.operatingPolicy.focusCities);
  return canonical.cities.filter((city) => hubs.has(city.code) || focusCities.has(city.code))
    .map((city) => ({...city, isHub: hubs.has(city.code)}))
    .sort((a, b) => Number(b.isHub) - Number(a.isHub) || a.code.localeCompare(b.code));
}

// Bank membership comes from the published assignments, including timing exceptions.
// A missing assignment is never inferred from proximity to a bank window.
export function buildHubBankBreakdown(canonical, hub) {
  const cities = new Map(canonical.cities.map((city) => [city.code, city]));
  const groups = [...new Set(canonical.cities.map((city) => city.group || "Unknown"))].sort();
  const makeBucket = (bank) => ({...bank, inbound: [], outbound: []});
  const banks = (canonical.hubBanks || []).filter((bank) => bank.hub === hub)
    .sort((a, b) => operatingMinute(a.startMinute) - operatingMinute(b.startMinute) || a.id.localeCompare(b.id))
    .map((bank) => makeBucket({...bank, label: bank.id.replace(`${hub}-`, "")}));
  const banksById = new Map(banks.map((bank) => [bank.id, bank]));
  const unassigned = makeBucket({id: "unassigned", label: "Unassigned to a bank"});
  const assignments = new Map();
  (canonical.bankAssignments || []).forEach((assignment) => {
    const key = `${assignment.legId}:${assignment.operation}`;
    if (!assignments.has(key)) assignments.set(key, new Set());
    assignments.get(key).add(assignment.bankId);
  });
  canonical.legs.forEach((leg) => {
    ["arrival", "departure"].forEach((operation) => {
      if ((operation === "arrival" ? leg.destination : leg.origin) !== hub) return;
      const cityCode = operation === "arrival" ? leg.origin : leg.destination;
      const city = cities.get(cityCode);
      const group = city?.group || "Unknown";
      if (!groups.includes(group)) groups.push(group);
      const assignedIds = [...(assignments.get(`${leg.id}:${operation}`) || [])];
      const bank = assignedIds.length === 1 ? banksById.get(assignedIds[0]) : null;
      const minute = leg[`${operation}Minute`];
      (bank || unassigned)[operation === "arrival" ? "inbound" : "outbound"].push({
        ...leg, city: cityCode, cityName: city?.displayName || city?.name || cityCode,
        group, minute, outsideWindow: Boolean(bank && !insideWindow(minute, bank)),
      });
    });
  });
  groups.sort();
  const rows = [...banks, unassigned];
  rows.forEach((bank) => {
    [bank.inbound, bank.outbound].forEach((flights) => flights.sort((a, b) => operatingMinute(a.minute) - operatingMinute(b.minute) || Number(a.flight) - Number(b.flight)));
    bank.groups = groups.map((code) => ({
      code, inbound: bank.inbound.filter((flight) => flight.group === code),
      outbound: bank.outbound.filter((flight) => flight.group === code),
    }));
    bank.inboundGroups = bank.groups.filter((group) => group.inbound.length).length;
    bank.outboundGroups = bank.groups.filter((group) => group.outbound.length).length;
    bank.bothGroups = bank.groups.filter((group) => group.inbound.length && group.outbound.length).length;
    bank.outsideWindow = [...bank.inbound, ...bank.outbound].filter((flight) => flight.outsideWindow).length;
  });
  return {
    hub, groups, banks, unassigned,
    inbound: rows.reduce((total, bank) => total + bank.inbound.length, 0),
    outbound: rows.reduce((total, bank) => total + bank.outbound.length, 0),
    maxGroupCount: Math.max(1, ...rows.flatMap((bank) => bank.groups.flatMap((group) => [group.inbound.length, group.outbound.length]))),
  };
}
