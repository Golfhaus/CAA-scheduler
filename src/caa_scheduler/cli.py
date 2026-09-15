from __future__ import annotations

import argparse
from pathlib import Path

from .allocation import build_frequency_fleet_plan_from_manifest
from .baseline import build_baseline
from .candidate import build_candidate
from .demand import build_demand_plan_from_manifest
from .gate_export import export_gate_schedule
from .io import read_json, write_json
from .operating_validation import validate_operating_rules
from .planning import reconstruct_planning_snapshot, validate_planning_snapshot
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
        return 0 if (
            validation["status"] == "pass"
            and result["timetableParity"]
            and result["timetableByteParity"]
            and result["gateParity"]
            and result["gateByteParity"]
            and result["planningValidation"]["status"] == "pass"
            and result["demandPlan"]["status"] == "pass"
            and result["frequencyFleetPlan"]["status"] == "pass"
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
    return 2
