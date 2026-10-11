"""Independent reference solver tests for LoadLens.

The reference solver uses exhaustive brute-force enumeration of all possible
split-point placements. It is COMPLETELY INDEPENDENT of the production binary-
search solver — it does not import or call optimize_allocation.

Purpose: cross-validate the production solver's optimum against this reference
for small inputs to detect algorithmic bugs.

The reference solver is O(C(n-1,k-1)) and suitable only for small n/k in tests.
"""

from __future__ import annotations

import itertools
import math
import random
from typing import List, Sequence, Tuple

import pytest

from loadlens.algorithms.allocation import optimize_allocation
from loadlens.models import Task


# ── Reference solver (brute-force) ────────────────────────────────────────────

def _brute_force_optimum(durations: Sequence[int], k: int) -> int:
    """Enumerate all C(n-1, k-1) split-point placements and return the minimum max-sum.

    This function does NOT use binary search or any part of the production solver.
    It is used exclusively for correctness cross-checking in tests.

    Args:
        durations: Ordered sequence of positive integer task durations.
        k: Number of workers / groups.

    Returns:
        Minimum achievable maximum group sum.
    """
    n = len(durations)
    if k == 1:
        return sum(durations)
    if k >= n:
        return max(durations)

    prefix = [0] * (n + 1)
    for i, d in enumerate(durations):
        prefix[i + 1] = prefix[i] + d

    def group_sum(start: int, end: int) -> int:
        return prefix[end + 1] - prefix[start]

    best = math.inf
    # Choose k-1 split points from positions 1..n-1 (split between index i-1 and i)
    for splits in itertools.combinations(range(1, n), k - 1):
        boundaries = [0] + list(splits) + [n]
        max_sum = max(
            group_sum(boundaries[i], boundaries[i + 1] - 1)
            for i in range(len(boundaries) - 1)
        )
        if max_sum < best:
            best = max_sum

    return int(best)


def make_tasks(*durations: int) -> List[Task]:
    return [Task(f"T{i+1}", d) for i, d in enumerate(durations)]


# ── Cross-validation tests ────────────────────────────────────────────────────

class TestReferenceVsProduction:
    """Compare production solver against independent brute-force reference."""

    def _cross_check(self, durations, k):
        tasks = make_tasks(*durations)
        expected = _brute_force_optimum(durations, k)
        result = optimize_allocation(tasks, k)
        assert result.optimal_capacity == expected, (
            f"durations={durations}, k={k}: "
            f"production={result.optimal_capacity}, brute-force={expected}"
        )

    def test_spec_example(self):
        self._cross_check([7, 2, 5, 10, 8], 3)

    def test_single_task(self):
        self._cross_check([42], 1)

    def test_two_tasks_one_worker(self):
        self._cross_check([3, 7], 1)

    def test_two_tasks_two_workers(self):
        self._cross_check([3, 7], 2)

    def test_equal_durations(self):
        self._cross_check([5, 5, 5, 5], 2)

    def test_all_workers(self):
        self._cross_check([1, 9, 2, 8, 3], 5)

    def test_large_single_task(self):
        self._cross_check([1, 1, 1, 100], 2)

    def test_ascending_durations(self):
        self._cross_check([1, 2, 3, 4, 5], 3)

    def test_descending_durations(self):
        self._cross_check([5, 4, 3, 2, 1], 3)

    def test_all_same_two_workers(self):
        self._cross_check([3, 3, 3, 3, 3], 2)

    def test_random_seed_42(self):
        """Seeded random test for reproducibility."""
        rng = random.Random(42)
        for _ in range(30):
            n = rng.randint(2, 8)
            k = rng.randint(1, n)
            durations = [rng.randint(1, 20) for _ in range(n)]
            self._cross_check(durations, k)

    def test_random_seed_1337(self):
        """Second seeded random test for additional coverage."""
        rng = random.Random(1337)
        for _ in range(30):
            n = rng.randint(2, 9)
            k = rng.randint(1, n)
            durations = [rng.randint(1, 50) for _ in range(n)]
            self._cross_check(durations, k)


# ── Brute-force self-tests ────────────────────────────────────────────────────

class TestBruteForceItself:
    """Sanity-check the brute-force reference solver."""

    def test_one_worker(self):
        assert _brute_force_optimum([3, 7, 2], 1) == 12

    def test_n_workers(self):
        assert _brute_force_optimum([3, 7, 2], 3) == 7

    def test_known_answer(self):
        assert _brute_force_optimum([7, 2, 5, 10, 8], 3) == 14
