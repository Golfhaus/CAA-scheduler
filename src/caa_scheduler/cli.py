from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .allocation import build_frequency_fleet_plan_from_manifest
from .bank_placement import build_hub_bank_plan_from_manifest
from .bank_materialization import build_bank_materialization_diagnostic_from_manifest
from .baseline import build_baseline
from .candidate import build_candidate
from .demand import build_demand_plan_from_manifest
from .exact_materialization import (
    ExactGlobalRepairIncomplete,
    ExactSeedStageComplete,
    build_exact_materialization_plan_from_manifest,
)
from .gate_export import export_gate_schedule
from .io import read_json, write_json
from .operating_validation import validate_operating_rules
from .planning import reconstruct_planning_snapshot, validate_planning_snapshot
from .routing import build_aircraft_route_plan_from_manifest
from .routing_repair import build_routing_repair_plan_from_manifest
from .timetable import export_timetable
from .validation import validate_schedule
from .web_build import build_web_console


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="caa-scheduler")
    subcommands = parser.add_subparsers(dest="command", required=True)

    baseline = subcommands.add_parser("baseline", help="Build and verify a golden baseline")
    baseline.add_argument("--config", type=Path, required=True)
    baseline.add_argument("--repo-root", type=Path, default=Path.cwd())

    candidate = subcommands.add_parser(
        "build-candidate",
        help="Compile an approved build configuration into a candidate package",
    )
    candidate.add_argument("config", type=Path)
    candidate.add_argument("--baseline", type=Path)
    candidate.add_argument("--output", type=Path)
    candidate.add_argument("--repo-root", type=Path, default=Path.cwd())

    validate = subcommands.add_parser("validate", help="Validate a canonical schedule")
    validate.add_argument("canonical", type=Path)
    validate.add_argument("--output", type=Path)

    timetable = subcommands.add_parser("export-timetable", help="Export timetable JSON")
    timetable.add_argument("canonical", type=Path)
    timetable.add_argument("output", type=Path)

    gates = subcommands.add_parser("export-gates", help="Export gate JSON")
    gates.add_argument("canonical", type=Path)
    gates.add_argument("output", type=Path)

    operating = subcommands.add_parser(
        "validate-operating", help="Validate operating rules and constraints"
    )
    operating.add_argument("canonical", type=Path)
    operating.add_argument("--output", type=Path)

    planning = subcommands.add_parser(
        "reconstruct-plan",
        help="Reconstruct and validate a durable planning snapshot from canonical JSON",
    )
    planning.add_argument("canonical", type=Path)
    planning.add_argument("output", type=Path)
    planning.add_argument("--validation-output", type=Path)
    planning.add_argument("--demand-version")

    demand = subcommands.add_parser(
        "build-demand-plan",
        help="Validate pinned demand inputs and compute multi-hub assignments",
    )
    demand.add_argument("canonical", type=Path)
    demand.add_argument("manifest", type=Path)
    demand.add_argument("output", type=Path)
    demand.add_argument("--repo-root", type=Path, default=Path.cwd())

    allocation = subcommands.add_parser(
        "build-frequency-plan",
        help="Allocate fresh frequencies and fleets from pinned demand inputs",
    )
    allocation.add_argument("canonical", type=Path)
    allocation.add_argument("demand_plan", type=Path)
    allocation.add_argument("manifest", type=Path)
    allocation.add_argument("output", type=Path)
    allocation.add_argument("--repo-root", type=Path, default=Path.cwd())

    banks = subcommands.add_parser(
        "build-bank-plan",
        help="Generate curfew-safe hub-bank windows and place proposed hub flying",
    )
    banks.add_argument("canonical", type=Path)
    banks.add_argument("frequency_plan", type=Path)
    banks.add_argument("manifest", type=Path)
    banks.add_argument("output", type=Path)
    banks.add_argument("--repo-root", type=Path, default=Path.cwd())

    routes = subcommands.add_parser(
        "build-route-plan",
        help="Construct aircraft cycles and evaluate fleet and RON feasibility",
    )
    routes.add_argument("canonical", type=Path)
    routes.add_argument("frequency_plan", type=Path)
    routes.add_argument("bank_plan", type=Path)
    routes.add_argument("manifest", type=Path)
    routes.add_argument("output", type=Path)
    routes.add_argument("--repo-root", type=Path, default=Path.cwd())

    repair = subcommands.add_parser(
        "build-routing-repair",
        help="Build a fleet-feasible, curfew-safe topology and RON repair plan",
    )
    repair.add_argument("canonical", type=Path)
    repair.add_argument("frequency_plan", type=Path)
    repair.add_argument("bank_plan", type=Path)
    repair.add_argument("manifest", type=Path)
    repair.add_argument("output", type=Path)
    repair.add_argument("--repo-root", type=Path, default=Path.cwd())

    materialization = subcommands.add_parser(
        "diagnose-bank-materialization",
        help="Prove the fleet lower bound for independent directional bank assignment",
    )
    materialization.add_argument("canonical", type=Path)
    materialization.add_argument("frequency_plan", type=Path)
    materialization.add_argument("bank_plan", type=Path)
    materialization.add_argument("manifest", type=Path)
    materialization.add_argument("output", type=Path)
    materialization.add_argument("--repo-root", type=Path, default=Path.cwd())

    exact = subcommands.add_parser(
        "build-exact-materialization",
        help="Integrate every leg into exact banked aircraft cycles",
    )
    exact.add_argument("canonical", type=Path)
    exact.add_argument("frequency_plan", type=Path)
    exact.add_argument("bank_plan", type=Path)
    exact.add_argument("repair_plan", type=Path)
    exact.add_argument("manifest", type=Path)
    exact.add_argument("output", type=Path)
    exact.add_argument("--repo-root", type=Path, default=Path.cwd())
    exact.add_argument("--seed-checkpoint", type=Path)
    exact.add_argument("--seed-fleets-per-run", type=int)
    exact.add_argument("--progress", action="store_true")

    web = subcommands.add_parser(
        "build-web", help="Assemble the static GitHub Pages console"
    )
    web.add_argument("--manifest", type=Path, default=Path("web/schedules.json"))
    web.add_argument("--output", type=Path, default=Path("dist"))
    web.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "build-candidate":
        report = build_candidate(
            args.config,
            args.repo_root,
            baseline_path=args.baseline,
            output_directory=args.output,
        )
        print(f"Candidate build: {report['status']}")
        print(f"Output: {report['outputDirectory']}")
        for blocker in report.get("blockers", []):
            print(f"  BLOCKED: {blocker}")
        for hard_stop in report.get("hardStops", []):
            print(
                f"  HARD STOP: {hard_stop['title']} "
                f"({hard_stop['findingCount']} findings)"
            )
        return 0 if report["status"] in {
            "candidate_ready",
            "candidate_review_required",
        } else 1
    if args.command == "build-web":
        result = build_web_console(
            args.manifest,
            args.repo_root,
            args.output,
        )
        print(
            f"Web console: {result['outputDirectory']} "
            f"({result['scheduleCount']} schedule, "
            f"{result['dataFileCount']} data files)"
        )
        return 0
    if args.command == "baseline":
        result = build_baseline(args.config, args.repo_root.resolve())
        validation = result["validation"]
        print(f"Canonical schedule: {result['canonicalPath']}")
        print(f"Validation: {validation['status']} ({validation['summary']['passed']}/{validation['summary']['checks']} checks)")
        print(f"Timetable parity: {'PASS' if result['timetableParity'] else 'FAIL'}")
        print(f"Timetable byte parity: {'PASS' if result['timetableByteParity'] else 'FAIL'}")
        print(f"Gate parity: {'PASS' if result['gateParity'] else 'FAIL'}")
        print(f"Gate byte parity: {'PASS' if result['gateByteParity'] else 'FAIL'}")
        operating = result["operatingValidation"]
        print(
            "Operating rules: "
            f"{operating['status'].upper()} "
            f"({operating['summary']['effectiveErrorFindings']} errors, "
            f"{operating['summary']['effectiveWarningFindings']} warnings, "
            f"{operating['summary']['notEvaluated']} not evaluated)"
        )
        planning = result["planningValidation"]
        print(
            "Planning snapshot: "
            f"{planning['status'].upper()} "
            f"({planning['summary']['passed']}/{planning['summary']['checks']} checks)"
        )
        demand = result["demandPlan"]
        parity = demand["assignmentParity"]
        print(
            "Demand plan: "
            f"{demand['status'].upper()} "
            f"({demand['matrix']['airportCount']} cities, "
            f"{parity['matched']}/{parity['compared']} hub assignments matched)"
        )
        allocation = result["frequencyFleetPlan"]
        print(
            "Frequency/fleet plan: "
            f"{allocation['status'].upper()} "
            f"({allocation['summary']['plannedLegs']} legs, "
            f"{allocation['summary']['candidateMarkets']} markets)"
        )
        bank_plan = result["hubBankPlan"]
        print(
            "Hub-bank plan: "
            f"{bank_plan['status'].upper()} "
            f"({bank_plan['summary']['placedLegs']}/"
            f"{bank_plan['summary']['hubMarketLegs']} hub legs placed, "
            f"{bank_plan['summary']['curfewViolations']} curfew violations)"
        )
        route_plan = result["aircraftRoutePlan"]
        print(
            "Aircraft route plan: "
            f"{route_plan['status'].upper()} "
            f"({route_plan['summary']['routedLegs']}/"
            f"{route_plan['summary']['plannedLegs']} legs routed, "
            f"{route_plan['summary']['aircraftShortfall']} aircraft short)"
        )
        repair_plan = result["routingRepairPlan"]
        print(
            "Routing repair: "
            f"{repair_plan['status'].upper()} "
            f"({repair_plan['summary']['routedLegs']}/"
            f"{repair_plan['summary']['plannedLegs']} legs, "
            f"{repair_plan['summary']['requiredAircraft']}/"
            f"{repair_plan['summary']['configuredAircraft']} aircraft; "
            f"{repair_plan['materializationStatus']})"
        )
        materialization = result["bankMaterializationDiagnostic"]
        print(
            "Bank materialization: "
            f"{materialization['status'].upper()} "
            f"({materialization['summary']['bankAndRonMinimumAircraft']}/"
            f"{materialization['summary']['configuredAircraft']} aggregate lower bound; "
            f"{materialization['summary']['fleetAllocationShortfall']} fleet-specific shortfall)"
        )
        exact = result["exactMaterializationPlan"]
        print(
            "Exact materialization: "
            f"{exact['status'].upper()} "
            f"({exact['summary']['routedLegs']}/"
            f"{exact['summary']['plannedLegs']} legs, "
            f"{exact['summary']['requiredAircraft']}/"
            f"{exact['summary']['configuredAircraft']} aircraft, "
            f"{exact['summary']['curfewViolations']} curfew violations)"
        )
        return 0 if (
            validation["status"] == "pass"
            and result["timetableParity"]
            and result["timetableByteParity"]
            and result["gateParity"]
            and result["gateByteParity"]
            and result["planningValidation"]["status"] == "pass"
            and result["demandPlan"]["status"] == "pass"
            and result["frequencyFleetPlan"]["status"] == "pass"
            and result["hubBankPlan"]["status"] == "pass"
            and result["routingRepairPlan"]["status"] == "pass"
            and result["exactMaterializationPlan"]["status"] == "pass"
        ) else 1

    canonical = read_json(args.canonical)
    if args.command == "validate":
        report = validate_schedule(canonical)
        if args.output:
            write_json(args.output, report)
        print(f"Validation: {report['status']} ({report['summary']['passed']}/{report['summary']['checks']} checks)")
        for check in report["checks"]:
            print(f"  {check['status'].upper():4} {check['id']}: {check['message']}")
        return 0 if report["status"] == "pass" else 1

    if args.command == "export-timetable":
        write_json(
            args.output,
            export_timetable(canonical),
            indent=1,
            trailing_newline=False,
        )
        print(f"Wrote {args.output}")
        return 0
    if args.command == "export-gates":
        write_json(
            args.output,
            export_gate_schedule(canonical),
            indent=1,
            trailing_newline=False,
        )
        print(f"Wrote {args.output}")
        return 0
    if args.command == "validate-operating":
        report = validate_operating_rules(canonical)
        if args.output:
            write_json(args.output, report)
        print(
            f"Operating validation: {report['status'].upper()} "
            f"({report['summary']['effectiveErrorFindings']} errors, "
            f"{report['summary']['effectiveWarningFindings']} warnings, "
            f"{report['summary']['notEvaluated']} not evaluated)"
        )
        for check in report["checks"]:
            print(f"  {check['status'].upper():13} {check['id']}: {check['message']}")
        return 0 if report["status"] != "fail" else 1
    if args.command == "reconstruct-plan":
        snapshot = reconstruct_planning_snapshot(
            canonical,
            demand_data_version=args.demand_version,
        )
        report = validate_planning_snapshot(snapshot, canonical)
        write_json(args.output, snapshot)
        if args.validation_output:
            write_json(args.validation_output, report)
        print(
            f"Planning snapshot: {report['status'].upper()} "
            f"({report['summary']['passed']}/{report['summary']['checks']} checks)"
        )
        print(f"Wrote {args.output}")
        return 0 if report["status"] == "pass" else 1
    if args.command == "build-demand-plan":
        expected = {
            city["code"]: city["hubAssignments"]
            for city in canonical["cities"]
            if city["role"] != "hub"
        }
        plan = build_demand_plan_from_manifest(
            args.manifest,
            args.repo_root.resolve(),
            canonical["cities"],
            expected_hub_assignments=expected,
        )
        write_json(args.output, plan)
        parity = plan["assignmentParity"]
        print(
            f"Demand plan: {plan['status'].upper()} "
            f"({plan['matrix']['airportCount']} cities, "
            f"{parity['matched']}/{parity['compared']} hub assignments matched)"
        )
        print(f"Wrote {args.output}")
        return 0 if plan["status"] == "pass" else 1
    if args.command == "build-frequency-plan":
        demand_plan = read_json(args.demand_plan)
        plan = build_frequency_fleet_plan_from_manifest(
            canonical,
            demand_plan,
            args.manifest,
            args.repo_root.resolve(),
        )
        write_json(args.output, plan)
        print(
            f"Frequency/fleet plan: {plan['status'].upper()} "
            f"({plan['summary']['plannedLegs']} legs, "
            f"{plan['summary']['candidateMarkets']} markets)"
        )
        print(f"Wrote {args.output}")
        return 0 if plan["status"] == "pass" else 1
    if args.command == "build-bank-plan":
        frequency_plan = read_json(args.frequency_plan)
        plan = build_hub_bank_plan_from_manifest(
            canonical,
            frequency_plan,
            args.manifest,
            args.repo_root.resolve(),
        )
        write_json(args.output, plan)
        print(
            f"Hub-bank plan: {plan['status'].upper()} "
            f"({plan['summary']['placedLegs']}/"
            f"{plan['summary']['hubMarketLegs']} hub legs placed, "
            f"{plan['summary']['curfewViolations']} curfew violations)"
        )
        print(f"Wrote {args.output}")
        return 0 if plan["status"] == "pass" else 1
    if args.command == "build-route-plan":
        frequency_plan = read_json(args.frequency_plan)
        bank_plan = read_json(args.bank_plan)
        plan = build_aircraft_route_plan_from_manifest(
            canonical,
            frequency_plan,
            bank_plan,
            args.manifest,
            args.repo_root.resolve(),
        )
        write_json(args.output, plan)
        print(
            f"Aircraft route plan: {plan['status'].upper()} "
            f"({plan['summary']['routedLegs']}/"
            f"{plan['summary']['plannedLegs']} legs routed, "
            f"{plan['summary']['aircraftShortfall']} aircraft short)"
        )
        print(f"Wrote {args.output}")
        return 0 if plan["status"] == "pass" else 1
    if args.command == "build-routing-repair":
        frequency_plan = read_json(args.frequency_plan)
        bank_plan = read_json(args.bank_plan)
        plan = build_routing_repair_plan_from_manifest(
            canonical,
            frequency_plan,
            bank_plan,
            args.manifest,
            args.repo_root.resolve(),
        )
        write_json(args.output, plan, indent=None)
        print(
            f"Routing repair: {plan['status'].upper()} "
            f"({plan['summary']['routedLegs']}/"
            f"{plan['summary']['plannedLegs']} legs, "
            f"{plan['summary']['requiredAircraft']}/"
            f"{plan['summary']['configuredAircraft']} aircraft)"
        )
        print(f"Materialization: {plan['materializationStatus']}")
        print(f"Wrote {args.output}")
        return 0 if plan["status"] == "pass" else 1
    if args.command == "diagnose-bank-materialization":
        frequency_plan = read_json(args.frequency_plan)
        bank_plan = read_json(args.bank_plan)
        diagnostic = build_bank_materialization_diagnostic_from_manifest(
            canonical,
            frequency_plan,
            bank_plan,
            args.manifest,
            args.repo_root.resolve(),
        )
        write_json(args.output, diagnostic)
        print(
            f"Bank materialization: {diagnostic['status'].upper()} "
            f"({diagnostic['summary']['fleetAllocationShortfall']} "
            "fleet-specific aircraft short)"
        )
        print(f"Wrote {args.output}")
        return 0 if diagnostic["materializationStatus"] != "blocked" else 1
    if args.command == "build-exact-materialization":
        if args.progress:
            logging.basicConfig(level=logging.INFO, format="%(message)s")
        frequency_plan = read_json(args.frequency_plan)
        bank_plan = read_json(args.bank_plan)
        repair_plan = read_json(args.repair_plan)
        try:
            plan = build_exact_materialization_plan_from_manifest(
                canonical,
                frequency_plan,
                bank_plan,
                repair_plan,
                args.manifest,
                args.repo_root.resolve(),
                args.seed_checkpoint,
                args.seed_fleets_per_run,
            )
        except ExactSeedStageComplete as result:
            print(str(result))
            return 0
        except ExactGlobalRepairIncomplete as result:
            print(str(result))
            return 1
        write_json(args.output, plan, indent=None)
        print(
            f"Exact materialization: {plan['status'].upper()} "
            f"({plan['summary']['routedLegs']}/"
            f"{plan['summary']['plannedLegs']} legs, "
            f"{plan['summary']['requiredAircraft']}/"
            f"{plan['summary']['configuredAircraft']} aircraft)"
        )
        print(f"Wrote {args.output}")
        return 0 if plan["status"] == "pass" else 1
    return 2
