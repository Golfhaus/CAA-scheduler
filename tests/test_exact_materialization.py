from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.exact_materialization import (
    _apply_assigned_bank_waves,
    _assigned_bank_windows_hold,
    _capacity_repair_stations,
    _expand_flexible_seed_types_to_hub_operations,
    _expand_flexible_seed_types_to_markets,
    _materialized_passenger_gate_overflow,
    _materialized_physical_capacity_overflow,
    _materialized_gate_assignments,
    _materialized_station_gate_assignments,
    _pairing_patterns,
    _read_exact_seed_checkpoint,
    _repair_gate_capacity_with_missions,
    _repair_successor_cycles,
    _repair_successor_gate_capacity,
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

    def test_materialized_capacity_counts_cyclic_ground_inventory(self) -> None:
        materialized = {}
        for ordinal in (1, 2):
            materialized[f"OUT-{ordinal}"] = {
                "id": f"OUT-{ordinal}",
                "fleet": "CRJ700",
                "origin": "AAA",
                "destination": "BBB",
                "departureUtcMinute": 0,
                "blockMinutes": 60,
            }
            materialized[f"BACK-{ordinal}"] = {
                "id": f"BACK-{ordinal}",
                "fleet": "CRJ700",
                "origin": "BBB",
                "destination": "AAA",
                "departureUtcMinute": 120,
                "blockMinutes": 60,
            }
        cities = {
            code: {
                "role": "destination",
                "gateAllocationOverride": gates,
                "standAllocationOverride": stands,
            }
            for code, gates, stands in (
                ("AAA", 1, 0),
                ("BBB", 2, 0),
            )
        }

        overflow = _materialized_physical_capacity_overflow(
            materialized,
            cities,
            30,
        )

        self.assertEqual(overflow[("AAA", 180)], 1)
        self.assertNotIn(("BBB", 60), overflow)

    def test_materialized_passenger_gate_overflow_counts_touch_windows(self) -> None:
        materialized = {
            f"IN-{ordinal}": {
                "id": f"IN-{ordinal}",
                "fleet": "CRJ200",
                "origin": origin,
                "destination": "AAA",
                "departureUtcMinute": 60,
                "blockMinutes": 60,
            }
            for ordinal, origin in enumerate(("BBB", "CCC", "DDD"), 1)
        }
        cities = {
            code: {
                "role": "destination",
                "timezone": "Eastern",
                "gateAllocationOverride": gates,
                "standAllocationOverride": 2,
            }
            for code, gates in (
                ("AAA", 2),
                ("BBB", 2),
                ("CCC", 2),
                ("DDD", 2),
            )
        }

        overflow = _materialized_passenger_gate_overflow(
            materialized,
            cities,
        )
        reserved_overflow = _materialized_passenger_gate_overflow(
            materialized,
            cities,
            {"AAA": 1},
        )

        self.assertEqual(overflow[("AAA", 120)], 1)
        self.assertEqual(reserved_overflow[("AAA", 120)], 2)

    def test_capacity_repair_unlocks_every_passenger_overloaded_station(self) -> None:
        selected = _capacity_repair_stations(
            {
                ("PHYSICAL_A", 100): 2,
                ("PHYSICAL_B", 200): 1,
            },
            {
                ("BHM", 100): 1,
                ("BNA", 200): 1,
                ("DAL", 300): 1,
                ("RFD", 400): 1,
            },
        )

        self.assertEqual(
            selected,
            {"PHYSICAL_A", "BHM", "BNA", "DAL", "RFD"},
        )

    def test_gate_time_shift_must_stay_in_its_assigned_bank(self) -> None:
        windows = {
            "AAA": [
                {"id": "AAA-B1", "startMinute": 100, "endMinute": 160},
                {"id": "AAA-B2", "startMinute": 200, "endMinute": 260},
            ],
            "BBB": [
                {"id": "BBB-B1", "startMinute": 300, "endMinute": 360}
            ],
        }
        leg = {
            "origin": "AAA",
            "destination": "BBB",
            "originBankId": "AAA-B1",
            "destinationBankId": "BBB-B1",
            "departureMinute": 120,
            "arrivalMinute": 330,
        }

        self.assertTrue(_assigned_bank_windows_hold(leg, windows))
        leg["departureMinute"] = 220
        self.assertFalse(_assigned_bank_windows_hold(leg, windows))

    def test_successor_choice_can_clear_a_concrete_gate_conflict(self) -> None:
        materialized = {
            **{
                f"A{index}": {
                    "id": f"A{index}",
                    "fleet": "CRJ200",
                    "origin": "BBB",
                    "destination": "AAA",
                    "departureUtcMinute": arrival - 60,
                    "blockMinutes": 60,
                }
                for index, arrival in enumerate((600, 660, 720))
            },
            **{
                f"D{index}": {
                    "id": f"D{index}",
                    "fleet": "CRJ200",
                    "origin": "AAA",
                    "destination": "BBB",
                    "departureUtcMinute": departure,
                    "blockMinutes": 60,
                }
                for index, departure in enumerate((600, 660, 720))
            },
        }
        cities = {
            "AAA": {
                "role": "destination",
                "timezone": "Eastern",
                "gateAllocationOverride": 1,
                "standAllocationOverride": 0,
            }
        }

        _, blocked = _materialized_station_gate_assignments(
            materialized,
            {"A0": "D0", "A1": "D2", "A2": "D1"},
            cities,
            40,
            "AAA",
        )
        _, repaired = _materialized_station_gate_assignments(
            materialized,
            {"A0": "D1", "A1": "D2", "A2": "D0"},
            cities,
            40,
            "AAA",
        )

        self.assertEqual(blocked["status"], "fail")
        self.assertEqual(repaired["status"], "pass")

    def test_gate_repair_continues_after_one_station_is_exhausted(self) -> None:
        failures = [
            {
                "station": "AAA",
                "strandedPassengerTouches": 2,
                "requiredGates": 2,
                "configuredGates": 1,
                "requiredStands": 0,
                "configuredStands": 0,
                "strandedLabels": ["A1 -> A1"],
            },
            {
                "station": "BBB",
                "strandedPassengerTouches": 1,
                "requiredGates": 2,
                "configuredGates": 1,
                "requiredStands": 0,
                "configuredStands": 0,
                "strandedLabels": ["B1 -> B1"],
            },
        ]
        legs = {
            "A1": {
                "id": "A1",
                "fleet": "CRJ200",
                "origin": "CCC",
                "destination": "AAA",
                "departureUtcMinute": 0,
                "blockMinutes": 60,
            },
            "B1": {
                "id": "B1",
                "fleet": "CRJ200",
                "origin": "CCC",
                "destination": "BBB",
                "departureUtcMinute": 0,
                "blockMinutes": 60,
            },
        }
        successors = {"A1": "A1", "B1": "B1"}
        station_results = {
            "AAA": {
                "status": "fail",
                "towMovements": 0,
                "failures": [
                    {**failures[0], "strandedLabels": ["A1 -> A1"]}
                ],
            },
            "BBB": {
                "status": "fail",
                "towMovements": 0,
                "failures": [
                    {**failures[1], "strandedLabels": ["B1 -> B1"]}
                ],
            },
        }
        full_result = {
            "status": "fail",
            "stations": 2,
            "towMovements": 0,
            "failures": failures,
        }

        with (
            patch(
                "caa_scheduler.exact_materialization._materialized_gate_assignments",
                return_value=({}, full_result),
            ),
            patch(
                "caa_scheduler.exact_materialization._materialized_station_gate_assignments",
                side_effect=lambda *args: ([], station_results[args[-1]]),
            ) as station_assignment,
        ):
            _repair_successor_gate_capacity(
                legs,
                successors,
                [],
                {"turns": {"minimumMinutes": 40}},
                {},
                set(),
                {"CRJ200": 1},
                10,
                False,
            )

        attempted = [call.args[-1] for call in station_assignment.call_args_list]
        self.assertEqual(attempted, ["AAA", "BBB"])

    def test_exact_gate_assignment_tows_only_the_long_hold_middle(self) -> None:
        materialized = {
            "ARRIVE": {
                "id": "ARRIVE",
                "fleet": "CRJ200",
                "origin": "BBB",
                "destination": "AAA",
                "departureUtcMinute": 1140,
                "blockMinutes": 60,
            },
            "DEPART": {
                "id": "DEPART",
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "BBB",
                "departureUtcMinute": 360,
                "blockMinutes": 60,
            },
            "TURN_IN": {
                "id": "TURN_IN",
                "fleet": "CRJ200",
                "origin": "CCC",
                "destination": "AAA",
                "departureUtcMinute": 1260,
                "blockMinutes": 40,
            },
            "TURN_OUT": {
                "id": "TURN_OUT",
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "CCC",
                "departureUtcMinute": 1360,
                "blockMinutes": 40,
            },
        }
        successors = {
            "ARRIVE": "DEPART",
            "DEPART": "ARRIVE",
            "TURN_IN": "TURN_OUT",
            "TURN_OUT": "TURN_IN",
        }
        cities = {
            code: {
                "role": "destination",
                "timezone": "Eastern",
                "gateAllocationOverride": gates,
                "standAllocationOverride": stands,
            }
            for code, gates, stands in (
                ("AAA", 1, 1),
                ("BBB", 2, 2),
                ("CCC", 2, 2),
            )
        }

        _, diagnostic = _materialized_gate_assignments(
            materialized,
            successors,
            cities,
            40,
        )

        self.assertEqual(diagnostic["status"], "pass")
        self.assertEqual(diagnostic["towMovements"], 1)

    def test_exact_gate_assignment_rejects_exhausted_inventory(self) -> None:
        materialized = {}
        successors = {}
        for ordinal in range(3):
            incoming = f"IN-{ordinal}"
            outgoing = f"OUT-{ordinal}"
            materialized[incoming] = {
                "id": incoming,
                "fleet": "CRJ200",
                "origin": "BBB",
                "destination": "AAA",
                "departureUtcMinute": 1200,
                "blockMinutes": 60,
            }
            materialized[outgoing] = {
                "id": outgoing,
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "BBB",
                "departureUtcMinute": 1320,
                "blockMinutes": 60,
            }
            successors[incoming] = outgoing
            successors[outgoing] = incoming
        cities = {
            code: {
                "role": "destination",
                "timezone": "Eastern",
                "gateAllocationOverride": gates,
                "standAllocationOverride": stands,
            }
            for code, gates, stands in (
                ("AAA", 1, 1),
                ("BBB", 3, 3),
            )
        }

        _, diagnostic = _materialized_gate_assignments(
            materialized,
            successors,
            cities,
            40,
        )

        self.assertEqual(diagnostic["status"], "fail")
        self.assertEqual(diagnostic["failures"][0]["station"], "AAA")

    def test_nonhub_can_add_historically_compatible_gate_relief_market(
        self,
    ) -> None:
        materialized = {
            "ARRIVE": {
                "id": "ARRIVE",
                "fleet": "CRJ200",
                "origin": "BBB",
                "destination": "AAA",
                "departureUtcMinute": 100,
                "blockMinutes": 60,
                "originBankId": None,
                "destinationBankId": None,
            },
            "DEPART": {
                "id": "DEPART",
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "BBB",
                "departureUtcMinute": 700,
                "blockMinutes": 60,
                "originBankId": None,
                "destinationBankId": None,
            },
            "OTHER_IN": {
                "id": "OTHER_IN",
                "fleet": "CRJ200",
                "origin": "CCC",
                "destination": "AAA",
                "departureUtcMinute": 180,
                "blockMinutes": 60,
                "originBankId": None,
                "destinationBankId": None,
            },
            "OTHER_OUT": {
                "id": "OTHER_OUT",
                "fleet": "CRJ200",
                "origin": "AAA",
                "destination": "CCC",
                "departureUtcMinute": 300,
                "blockMinutes": 60,
                "originBankId": None,
                "destinationBankId": None,
            },
        }
        successors = {
            "ARRIVE": "DEPART",
            "DEPART": "ARRIVE",
            "OTHER_IN": "OTHER_OUT",
            "OTHER_OUT": "OTHER_IN",
        }
        cities = {
            code: {
                "role": "destination",
                "timezone": "Eastern",
                "gateAllocationOverride": gates,
                "standAllocationOverride": stands,
                "latitude": latitude,
                "longitude": longitude,
            }
            for code, gates, stands, latitude, longitude in (
                ("AAA", 1, 0, 35.0, -80.0),
                ("BBB", 3, 1, 36.0, -80.0),
                ("CCC", 2, 1, 37.0, -80.0),
                ("DDD", 2, 1, 35.0, -79.0),
            )
        }
        policy = {
            "hubs": [],
            "focusCities": [],
            "departureWindows": {
                "earliestMinute": 0,
                "destinationLatestMinute": 1439,
                "hubOrFocusLatestMinute": 1439,
                "redEyeLatestMinute": 0,
                "redEyeArrivalMinimumMinute": 0,
                "redEyeArrivalMaximumMinute": 1439,
            },
            "turns": {"minimumMinutes": 40},
            "section26": {
                "hardFloorMinutes": 30,
                "pairingTargetMaximumMinutes": 240,
                "maximumCityDepartureGapMinutes": 240,
                "numeratorMinutes": 480,
                "stationReferenceDepartures": 4,
                "stationFactorMinimum": 0.7,
                "stationFactorMaximum": 1.8,
                "nearTargetTolerance": 0.9,
                "oneExceptionMinimumFrequency": 4,
            },
        }
        frequency_plan = {
            "markets": [
                {
                    "origin": "AAA",
                    "destination": "DDD",
                    "classification": "point_to_point",
                    "twoWayDemand": 100.0,
                    "plannedRoundTrips": 0,
                    "frequencyCeilingRoundTrips": 1,
                    "allocations": [],
                    "historicalFleetLegs": {"CRJ200": 2},
                }
            ]
        }
        windows = {}
        _, before = _materialized_station_gate_assignments(
            materialized, successors, cities, 40, "AAA"
        )
        self.assertEqual(before["status"], "fail")

        with patch(
            "caa_scheduler.exact_materialization._cycles",
            return_value=[{"fleet": "CRJ200", "aircraftRequired": 2}],
        ), patch(
            "caa_scheduler.exact_materialization._cycle_score",
            return_value=(0, 0, 0, 0, 0, 2),
        ), patch(
            "caa_scheduler.exact_materialization._pairing_spacing_holds_for_leg",
            return_value=True,
        ):
            _, additions = _repair_gate_capacity_with_missions(
                materialized,
                successors,
                [{"fleet": "CRJ200", "aircraftRequired": 2}],
                frequency_plan,
                policy,
                cities,
                windows,
                set(),
                {"CRJ200": 2},
                11,
                True,
                Counter(leg["origin"] for leg in materialized.values()),
                True,
                {
                    "targetStations": ["AAA"],
                    "minimumHoldMinutes": 240,
                    "minimumTwoWayDemand": 8.0,
                    "maximumMissions": 1,
                    "maximumTimingsPerHoldMarket": 4,
                },
                {
                    "CRJ200": {
                        "fleet": "CRJ200",
                        "blockMinutesPerNauticalMile": 0.1,
                        "blockMinutesIntercept": 30.0,
                    }
                },
            )

        _, after = _materialized_station_gate_assignments(
            materialized, successors, cities, 40, "AAA"
        )
        self.assertEqual(len(additions), 1)
        self.assertEqual(additions[0]["market"], ["AAA", "DDD"])
        self.assertTrue(additions[0]["newFrequency"])
        self.assertEqual(after["status"], "pass")

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
        over_ceiling_successors = dict(successors)
        (
            over_ceiling_successors["A"],
            over_ceiling_successors["C"],
        ) = (
            over_ceiling_successors["C"],
            over_ceiling_successors["A"],
        )
        over_ceiling_state = tuple(sorted(over_ceiling_successors.items()))
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
            elif state == over_ceiling_state:
                score = (0, 0, 0, 0, 0, 5)
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
