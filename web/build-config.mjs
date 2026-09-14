export const BUILD_CONFIG_SCHEMA_VERSION = "1.0.0";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function cleanString(value) {
  return String(value ?? "").trim();
}

function positiveInteger(value) {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : null;
}

function nonnegativeInteger(value) {
  const number = Number(value);
  return Number.isInteger(number) && number >= 0 ? number : null;
}

export function buildConfigId(number, version) {
  const safeVersion = cleanString(version).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  return `schedule_${number}_v${safeVersion || "draft"}`;
}

export function createBuildConfig(canonical, manifest) {
  const source = canonical.schedule;
  const nextNumber = Number(source.number) + 1;
  const version = "0.1.0";
  return {
    schemaVersion: BUILD_CONFIG_SCHEMA_VERSION,
    buildId: buildConfigId(nextNumber, version),
    schedule: {
      number: nextNumber,
      version,
      label: `Schedule ${nextNumber}`,
      mode: "mainline",
      status: "draft",
    },
    startingPoint: {
      kind: "previous_schedule",
      scheduleId: source.id,
    },
    fleetCounts: clone(source.fleetCounts || {}),
    connectionWindowMinutes: clone(source.connectionWindowMinutes || { minimum: 30, maximum: 240 }),
    inputs: {
      instructions: {
        version: cleanString(manifest?.instructions?.version),
        source: cleanString(manifest?.instructions?.source),
      },
      cityInformation: clone(canonical.provenance?.cityInformation || { filename: "", sha256: "" }),
      operatingPolicy: clone(canonical.provenance?.operatingPolicy || { filename: "", sha256: "" }),
      demandData: {
        version: cleanString(manifest?.buildSetup?.demandData?.version),
      },
    },
    networkChanges: [],
    notes: "",
  };
}

export function normalizeBuildConfig(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError("Build configuration must be a JSON object.");
  }
  const schedule = value.schedule && typeof value.schedule === "object" ? value.schedule : {};
  const number = Number(schedule.number);
  const version = cleanString(schedule.version);
  const counts = value.fleetCounts && typeof value.fleetCounts === "object" && !Array.isArray(value.fleetCounts)
    ? Object.fromEntries(Object.entries(value.fleetCounts).map(([fleet, count]) => [cleanString(fleet).toUpperCase(), Number(count)]))
    : {};
  const normalized = {
    schemaVersion: cleanString(value.schemaVersion) || BUILD_CONFIG_SCHEMA_VERSION,
    buildId: buildConfigId(number, version),
    schedule: {
      number,
      version,
      label: cleanString(schedule.label),
      mode: cleanString(schedule.mode),
      status: "draft",
    },
    startingPoint: {
      kind: cleanString(value.startingPoint?.kind),
      scheduleId: value.startingPoint?.kind === "blank" ? null : cleanString(value.startingPoint?.scheduleId),
    },
    fleetCounts: counts,
    connectionWindowMinutes: {
      minimum: Number(value.connectionWindowMinutes?.minimum),
      maximum: Number(value.connectionWindowMinutes?.maximum),
    },
    inputs: {
      instructions: {
        version: cleanString(value.inputs?.instructions?.version),
        source: cleanString(value.inputs?.instructions?.source),
      },
      cityInformation: {
        filename: cleanString(value.inputs?.cityInformation?.filename),
        sha256: cleanString(value.inputs?.cityInformation?.sha256),
      },
      operatingPolicy: {
        filename: cleanString(value.inputs?.operatingPolicy?.filename),
        sha256: cleanString(value.inputs?.operatingPolicy?.sha256),
      },
      demandData: {
        version: cleanString(value.inputs?.demandData?.version),
      },
    },
    networkChanges: Array.isArray(value.networkChanges)
      ? value.networkChanges.map((change) => ({
          airport: cleanString(change?.airport).toUpperCase(),
          action: cleanString(change?.action),
          targetStatus: cleanString(change?.targetStatus),
          notes: cleanString(change?.notes),
        }))
      : [],
    notes: cleanString(value.notes),
  };
  return normalized;
}

function check(id, title, status, message) {
  return { id, title, status, message };
}

export function validateBuildConfig(value, canonical) {
  let config;
  try {
    config = normalizeBuildConfig(value);
  } catch (error) {
    return {
      status: "fail",
      summary: { checks: 1, passed: 0, blocking: 1, warnings: 0, notEvaluated: 0 },
      checks: [check("document", "Configuration document", "fail", error.message)],
    };
  }

  const checks = [];
  const scheduleNumber = positiveInteger(config.schedule.number);
  const identityValid = scheduleNumber !== null
    && Boolean(config.schedule.version)
    && Boolean(config.schedule.label);
  checks.push(check(
    "schedule_identity",
    "Schedule identity",
    identityValid ? "pass" : "fail",
    identityValid
      ? `Schedule ${scheduleNumber}, version ${config.schedule.version}, is explicitly identified.`
      : "Schedule number, version, and label are required; the number must be a positive integer.",
  ));

  const modeValid = ["mainline", "skunkworks"].includes(config.schedule.mode);
  checks.push(check(
    "build_mode",
    "Build mode",
    modeValid ? "pass" : "fail",
    modeValid
      ? `${config.schedule.mode === "mainline" ? "Mainline" : "Skunkworks"} promotion rules will apply.`
      : "Build mode must be Mainline or Skunkworks.",
  ));

  const baselineIds = new Set([canonical?.schedule?.id].filter(Boolean));
  const startValid = config.startingPoint.kind === "blank"
    || (
      config.startingPoint.kind === "previous_schedule"
      && Boolean(config.startingPoint.scheduleId)
      && baselineIds.has(config.startingPoint.scheduleId)
    );
  checks.push(check(
    "starting_point",
    "Starting point",
    startValid ? "pass" : "fail",
    startValid
      ? (config.startingPoint.kind === "blank"
          ? "The schedule will start from a blank network plan."
          : `The schedule is pinned to ${config.startingPoint.scheduleId}.`)
      : "Choose a blank start or a published baseline available in this console.",
  ));

  const fleets = Object.entries(config.fleetCounts);
  const invalidFleets = fleets.filter(([fleet, count]) => !fleet || nonnegativeInteger(count) === null);
  const duplicateNames = fleets.length !== new Set(fleets.map(([fleet]) => fleet)).size;
  const fleetValid = fleets.length > 0 && invalidFleets.length === 0 && !duplicateNames;
  checks.push(check(
    "fleet_plan",
    "Schedule-specific fleet plan",
    fleetValid ? "pass" : "fail",
    fleetValid
      ? `${fleets.length} fleet type${fleets.length === 1 ? "" : "s"} and ${fleets.reduce((sum, [, count]) => sum + Number(count), 0)} aircraft are explicitly recorded for this schedule.`
      : "Add at least one uniquely named fleet type and use whole-number aircraft counts of zero or greater.",
  ));

  const minimum = nonnegativeInteger(config.connectionWindowMinutes.minimum);
  const maximum = nonnegativeInteger(config.connectionWindowMinutes.maximum);
  const connectionValid = minimum !== null && maximum !== null && maximum > minimum;
  checks.push(check(
    "connection_window",
    "Connection window",
    connectionValid ? "pass" : "fail",
    connectionValid
      ? `Connections are pinned to ${minimum}–${maximum} minutes.`
      : "Connection minimum and maximum must be whole minutes, and maximum must exceed minimum.",
  ));

  const pins = config.inputs;
  const instructionPinned = Boolean(pins.instructions.version && pins.instructions.source);
  const cityPinned = Boolean(pins.cityInformation.filename && /^[0-9a-f]{64}$/i.test(pins.cityInformation.sha256));
  const policyPinned = Boolean(pins.operatingPolicy.filename && /^[0-9a-f]{64}$/i.test(pins.operatingPolicy.sha256));
  const demandPinned = Boolean(pins.demandData.version);
  const pinsValid = instructionPinned && cityPinned && policyPinned && demandPinned;
  checks.push(check(
    "input_pins",
    "Pinned build inputs",
    pinsValid ? "pass" : "fail",
    pinsValid
      ? "Instructions, city information, operating policy, and demand data are explicitly pinned."
      : "Pin the instruction version/source, city and policy files with SHA-256 fingerprints, and a demand-data version.",
  ));

  const activeCities = new Map(
    (canonical?.cities || []).map((city) => [String(city.code).toUpperCase(), Boolean(city.active)])
  );
  const allowedActions = new Set(["add", "remove", "status_change"]);
  const allowedStatuses = new Set(["destination", "focus_city", "hub", "inactive"]);
  const seenAirports = new Set();
  const networkErrors = [];
  config.networkChanges.forEach((change, index) => {
    const label = change.airport || `row ${index + 1}`;
    if (!/^[A-Z0-9]{3,4}$/.test(change.airport)) networkErrors.push(`${label}: invalid airport code`);
    if (!allowedActions.has(change.action)) networkErrors.push(`${label}: invalid action`);
    if (seenAirports.has(change.airport)) networkErrors.push(`${label}: duplicate change`);
    seenAirports.add(change.airport);
    if (change.action === "add" && activeCities.get(change.airport)) networkErrors.push(`${label}: already active`);
    if (change.action === "remove" && !activeCities.get(change.airport)) networkErrors.push(`${label}: not an active city`);
    if (["add", "status_change"].includes(change.action) && !allowedStatuses.has(change.targetStatus)) {
      networkErrors.push(`${label}: target status is required`);
    }
  });
  checks.push(check(
    "network_changes",
    "Network changes",
    networkErrors.length ? "fail" : "pass",
    networkErrors.length
      ? networkErrors.join("; ")
      : (config.networkChanges.length
          ? `${config.networkChanges.length} proposed airport change${config.networkChanges.length === 1 ? "" : "s"} passed structural preflight.`
          : "No airport additions, removals, or status changes are proposed."),
  ));

  const additions = config.networkChanges.filter((change) => change.action === "add").length;
  checks.push(check(
    "airport_metadata",
    "Airport metadata and runway screening",
    additions ? "warning" : "pass",
    additions
      ? `${additions} airport addition${additions === 1 ? "" : "s"} will require complete city metadata, demand inputs, and runway screening before construction.`
      : "No new airport metadata or runway screening is required at setup.",
  ));

  checks.push(check(
    "curfew_enforcement",
    "Curfew enforcement",
    policyPinned ? "pass" : "fail",
    policyPinned
      ? "The pinned operating policy marks curfew violations as construction hard stops."
      : "Curfew hard-stop enforcement cannot be guaranteed until the operating policy is pinned.",
  ));

  const summary = {
    checks: checks.length,
    passed: checks.filter((item) => item.status === "pass").length,
    blocking: checks.filter((item) => item.status === "fail").length,
    warnings: checks.filter((item) => item.status === "warning").length,
    notEvaluated: checks.filter((item) => item.status === "not_evaluated").length,
  };
  return {
    status: summary.blocking ? "fail" : "pass",
    summary,
    checks,
  };
}

export function serializeBuildConfig(value) {
  return `${JSON.stringify(normalizeBuildConfig(value), null, 2)}\n`;
}

export function buildConfigFilename(value) {
  const config = normalizeBuildConfig(value);
  return `${config.buildId}_build_config.json`;
}
