from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.exact_materialization import (
    _apply_assigned_bank_waves,
    _expand_flexible_seed_types_to_hub_operations,
    _expand_flexible_seed_types_to_markets,
    _pairing_patterns,
    _read_exact_seed_checkpoint,
    _repair_successor_cycles,
    _write_exact_seed_checkpoint,
    blocked_exact_materialization_plan,
)


PLAN_PATH = (
    REPO_ROOT
    / "data"
    / "schedules"
    / "schedule_6_v2_2_5"
    / "exact_materialization_plan.json"
)


class ExactMaterializationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads(PLAN_PATH.read_text())

    def test_every_proposed_leg_has_an_exact_time(self) -> None:
        self.assertEqual(self.plan["status"], "pass")
        self.assertEqual(self.plan["materializationStatus"], "complete")
        self.assertEqual(self.plan["summary"]["plannedLegs"], 1430)
        self.assertEqual(self.plan["summary"]["routedLegs"], 1430)
        self.assertEqual(len(self.plan["legs"]), 1430)

    def test_banked_and_nonhub_flying_are_both_complete(self) -> None:
        self.assertEqual(self.plan["summary"]["bankTouchLegs"], 1190)
        self.assertEqual(self.plan["summary"]["bankAlignedLegs"], 1190)
        self.assertEqual(self.plan["summary"]["nonHubLegs"], 240)
        self.assertEqual(self.plan["summary"]["nonHubIntegratedLegs"], 240)

    def test_selected_fleet_and_hard_curfews_remain_intact(self) -> None:
        self.assertEqual(self.plan["summary"]["configuredAircraft"], 225)
        self.assertEqual(self.plan["summary"]["requiredAircraft"], 208)
        self.assertEqual(self.plan["summary"]["remainingAircraft"], 17)
        self.assertEqual(self.plan["summary"]["curfewViolations"], 0)
        self.assertEqual(self.plan["fleetPlan"]["CRJ200"]["requiredAircraft"], 78)
        self.assertEqual(self.plan["fleetPlan"]["CRJ200"]["configuredAircraft"], 80)

    def test_ron_requirements_are_verified_on_real_cycles(self) -> None:
        self.assertEqual(len(self.plan["ronAssignments"]), 99)
        self.assertEqual(self.plan["summary"]["destinationsWithoutRon"], 0)
        self.assertEqual(self.plan["summary"]["rollingRonViolations"], 0)
        self.assertEqual(self.plan["summary"]["successorSwaps"], 1)
        self.assertEqual(self.plan["nextStep"]["action"], "assign_canonical_identifiers")

    def test_bounded_solver_failure_is_a_durable_blocker(self) -> None:
        blocked = blocked_exact_materialization_plan(
            {
                "schedule": {
                    "id": "schedule_7_test",
                    "fleetCounts": {"CRJ200": 80},
                },
                "operatingPolicy": {"id": "test-policy"},
            },
            {"summary": {"plannedLegs": 1430}},
            "test-rules",
            "Exact CRJ200 materialization failed: time limit reached",
        )
        self.assertEqual(blocked["status"], "fail")
        self.assertEqual(blocked["materializationStatus"], "blocked")
        self.assertEqual(blocked["summary"]["plannedLegs"], 1430)
        self.assertEqual(
            blocked["nextStep"]["action"], "retry_exact_materialization"
        )
        self.assertIn("time limit", blocked["diagnostics"]["solverFailure"])

    def test_capacity_checked_bank_waves_are_attached_to_exact_copies(self) -> None:
        inventory = {
            "CRJ200": [
                {
                    "id": "AAA-HUB-CRJ200-01-OUT",
                    "fleet": "CRJ200",
                    "origin": "AAA",
                    "destination": "HUB",
                },
                {
                    "id": "AAA-HUB-CRJ200-02-OUT",
                    "fleet": "CRJ200",
                    "origin": "AAA",
                    "destination": "HUB",
                },
            ]
        }
        bank_plan = {
            "placements": [
                {
                    "id": "second",
                    "fleet": "CRJ200",
                    "origin": "AAA",
                    "destination": "HUB",
                    "roundTripOrdinal": 2,
                    "bankTouches": [
                        {
                            "hub": "HUB",
                            "operation": "arrival",
                            "bankId": "HUB-B2",
                        }
                    ],
                },
                {
                    "id": "first",
                    "fleet": "CRJ200",
                    "origin": "AAA",
                    "destination": "HUB",
                    "roundTripOrdinal": 1,
                    "bankTouches": [
                        {
                            "hub": "HUB",
                            "operation": "arrival",
                            "bankId": "HUB-B1",
                        }
                    ],
                },
            ]
        }
        _apply_assigned_bank_waves(inventory, bank_plan)
        self.assertEqual(
            [leg["destinationBankId"] for leg in inventory["CRJ200"]],
            ["HUB-B1", "HUB-B2"],
        )

    def test_pairing_patterns_compile_spacing_before_the_fleet_solve(self) -> None:
        candidates = [
            {"departureUtcMinute": minute, "cost": float(minute)}
            for minute in (0, 20, 40, 720)
        ]
        patterns = _pairing_patterns(
            candidates,
            frequency=2,
            minimum_gap=60.0,
            hard_floor=30.0,
            allowed_exceptions=0,
            reserved=[],
            maximum_patterns=20,
            beam_width=100,
        )
        departures = [
            tuple(event["departureUtcMinute"] for event in row["events"])
            for row in patterns
        ]
        self.assertIn((0, 720), departures)
        self.assertTrue(
            all(
                min((second - first) % 1440, (first - second) % 1440)
                >= 60
                for first, second in departures
            )
        )

    def test_seed_repair_retimes_both_directions_of_a_market(self) -> None:
        outbound = ("CRJ700", "HUB", "AAA", "hub_spoke", 60)
        inbound = ("CRJ700", "AAA", "HUB", "hub_spoke", 60)
        unrelated = ("CRJ700", "HUB", "BBB", "hub_spoke", 70)
        other_fleet = ("CRJ200", "AAA", "HUB", "hub_spoke", 60)

        expanded = _expand_flexible_seed_types_to_markets(
            {outbound},
            [
                (outbound, []),
                (inbound, []),
                (unrelated, []),
                (other_fleet, []),
            ],
        )

        self.assertEqual(expanded, {outbound, inbound})

    def test_seed_repair_expands_across_an_overloaded_hub_operation(self) -> None:
        jax_b14_departure = ("CRJ700", "JAX", "AAA", "hub_spoke", 60)
        jax_b1_departure = ("CRJ900", "JAX", "BBB", "hub_spoke", 70)
        jax_b13_departure = ("MAX9", "JAX", "CCC", "hub_spoke", 80)
        jax_arrival = ("CRJ200", "DDD", "JAX", "hub_spoke", 55)
        mci_departure = ("CRJ700", "MCI", "EEE", "hub_spoke", 65)
        touches = {
            jax_b14_departure: {("JAX-B14", "departure")},
            jax_b1_departure: {("JAX-B1", "departure")},
            jax_b13_departure: {("JAX-B13", "departure")},
            jax_arrival: {("JAX-B14", "arrival")},
            mci_departure: {("MCI-B14", "departure")},
        }
        windows = {
            "JAX": [
                {"id": "JAX-B1"},
                {"id": "JAX-B13"},
                {"id": "JAX-B14"},
            ],
            "MCI": [{"id": "MCI-B14"}],
        }

        expanded = _expand_flexible_seed_types_to_hub_operations(
            {jax_b14_departure},
            touches,
            {("JAX-B14", "departure")},
            windows,
        )

        self.assertEqual(
            expanded,
            {jax_b14_departure, jax_b1_departure, jax_b13_departure},
        )

    def test_successor_repair_can_cross_a_score_plateau(self) -> None:
        identifiers = ("A", "B", "C", "D")
        legs = {
            identifier: {
                "id": identifier,
                "fleet": "CRJ200",
                "destination": "HUB",
            }
            for identifier in identifiers
        }
        successors = {identifier: identifier for identifier in identifiers}
        base_state = tuple(sorted(successors.items()))
        plateau_successors = dict(successors)
        plateau_successors["A"], plateau_successors["B"] = (
            plateau_successors["B"],
            plateau_successors["A"],
        )
        plateau_state = tuple(sorted(plateau_successors.items()))
        passing_successors = dict(plateau_successors)
        passing_successors["C"], passing_successors["D"] = (
            passing_successors["D"],
            passing_successors["C"],
        )
        passing_state = tuple(sorted(passing_successors.items()))

        def fake_cycles(_legs, candidate_successors, *_args, **_kwargs):
            state = tuple(sorted(candidate_successors.items()))
            if state == passing_state:
                score = (0, 0, 0, 0, 0, 4)
                maximum_gap = 0
            elif state in {base_state, plateau_state}:
                score = (0, 0, 1, 1, 12, 4)
                maximum_gap = 12
            else:
                score = (0, 0, 1, 2, 13, 4)
                maximum_gap = 13
            return [
                {
                    "maximumDaysWithoutTargetRon": maximum_gap,
                    "legIds": list(identifiers),
                    "score": score,
                }
            ]

        with patch(
            "caa_scheduler.exact_materialization._cycles",
            side_effect=fake_cycles,
        ), patch(
            "caa_scheduler.exact_materialization._cycle_score",
            side_effect=lambda cycles, *_args: cycles[0]["score"],
        ):
            cycles, swaps = _repair_successor_cycles(
                legs,
                successors,
                {"turns": {"minimumMinutes": 40}},
                {},
                set(),
                {"CRJ200": 4},
                11,
                True,
            )

        self.assertEqual(cycles[0]["score"], (0, 0, 0, 0, 0, 4))
        self.assertEqual(
            [swap["moveKind"] for swap in swaps],
            ["plateau", "improvement"],
        )

    def test_exact_seed_checkpoint_round_trip_and_input_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            materialized = {
                "CRJ700": {
                    "AAA-HUB-01": {
                        "id": "AAA-HUB-01",
                        "fleet": "CRJ700",
                        "departureUtcMinute": 600,
                    }
                }
            }
            solvers = {"CRJ700": {"status": "feasible_time_limit"}}
            _write_exact_seed_checkpoint(
                path,
                "matching-fingerprint",
                ["CRJ700", "CRJ200"],
                materialized,
                solvers,
            )

            loaded_materialized, loaded_solvers = _read_exact_seed_checkpoint(
                path,
                "matching-fingerprint",
                ["CRJ700", "CRJ200"],
            )
            self.assertEqual(loaded_materialized, materialized)
            self.assertEqual(loaded_solvers, solvers)
            with self.assertRaisesRegex(ValueError, "does not match"):
                _read_exact_seed_checkpoint(
                    path,
                    "changed-input-fingerprint",
                    ["CRJ700", "CRJ200"],
                )


if __name__ == "__main__":
    unittest.main()
