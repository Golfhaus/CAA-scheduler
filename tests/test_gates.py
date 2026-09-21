from __future__ import annotations

import sys
import unittest
import random
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from caa_scheduler.gates import (
    GateClaim,
    _bounded_coloring,
    _conflict_graph,
    _greedy_coloring,
    _maximum_cyclic_concurrency,
    overlaps,
)


def claim(start: int, end: int, label: str) -> GateClaim:
    return GateClaim(start, end, label, "CRJ700", "turn", None, None)


class GateColoringTests(unittest.TestCase):
    def test_sweep_conflict_graph_matches_pairwise_overlap(self) -> None:
        randomizer = random.Random(714)
        claims = [
            claim(start, start + randomizer.randrange(1, 1440), str(index))
            for index, start in enumerate(
                randomizer.sample(range(-700, 2100), 100)
            )
        ]
        expected = [set() for _ in claims]
        for first in range(len(claims)):
            for second in range(first + 1, len(claims)):
                if overlaps(claims[first], claims[second]):
                    expected[first].add(second)
                    expected[second].add(first)
        self.assertEqual(_conflict_graph(claims), expected)

    def test_normalized_overlap_matches_shift_reference(self) -> None:
        def reference(first: GateClaim, second: GateClaim) -> bool:
            return any(
                first.start + first_shift < second.end + second_shift
                and second.start + second_shift < first.end + first_shift
                for first_shift in (-1440, 0, 1440)
                for second_shift in (-1440, 0, 1440)
            )

        randomizer = random.Random(713)
        claims = [
            claim(start, start + randomizer.randrange(1, 1440), str(index))
            for index, start in enumerate(
                randomizer.sample(range(-700, 2100), 100)
            )
        ]
        for first in claims:
            for second in claims:
                self.assertEqual(overlaps(first, second), reference(first, second))

    def test_incremental_dsatur_matches_reference_ordering(self) -> None:
        def reference(claims: list[GateClaim]) -> list[int]:
            adjacency = _conflict_graph(claims)
            colors = [0] * len(claims)
            for _ in claims:
                uncolored = [
                    index for index, color in enumerate(colors) if not color
                ]
                vertex = max(
                    uncolored,
                    key=lambda index: (
                        len(
                            {
                                colors[neighbor]
                                for neighbor in adjacency[index]
                                if colors[neighbor]
                            }
                        ),
                        len(adjacency[index]),
                        -index,
                    ),
                )
                unavailable = {
                    colors[neighbor]
                    for neighbor in adjacency[vertex]
                    if colors[neighbor]
                }
                colors[vertex] = next(
                    color
                    for color in range(1, len(claims) + 1)
                    if color not in unavailable
                )
            return colors

        randomizer = random.Random(712)
        claims = [
            claim(start, start + randomizer.randrange(30, 240), str(index))
            for index, start in enumerate(
                randomizer.sample(range(0, 1440, 5), 80)
            )
        ]
        self.assertEqual(_greedy_coloring(claims), reference(claims))

    def test_cyclic_concurrency_counts_wrapped_claims(self) -> None:
        claims = [
            claim(1380, 1500, "wrapped"),
            claim(0, 120, "morning"),
            claim(30, 90, "overlap"),
        ]
        self.assertEqual(_maximum_cyclic_concurrency(claims), 3)

    def test_concurrency_proof_skips_exact_coloring(self) -> None:
        claims = [
            claim(100, 200, "one"),
            claim(120, 220, "two"),
            claim(140, 240, "three"),
        ]
        with patch("caa_scheduler.gates.milp") as solver:
            self.assertIsNone(_bounded_coloring(claims, 2))
        solver.assert_not_called()


if __name__ == "__main__":
    unittest.main()
