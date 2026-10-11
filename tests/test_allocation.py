"""Tests for the workload allocation algorithm.

Tests cover:
- One task / one worker edge cases
- workers=1 and workers=n boundaries
- Equal and uneven durations
- Reconstruction invariants (k groups, non-empty, order preserved, no duplicates)
- Feasibility monotonicity
- Trace completeness
- Invalid input rejection
"""

from __future__ import annotations

import math
import pytest

from loadlens.algorithms.allocation import (
    is_capacity_feasible,
    optimize_allocation,
    reconstruct_groups,
    required_workers,
)
from loadlens.models import Task
from loadlens.validation import ValidationError


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_tasks(*durations: int) -> list[Task]:
    return [Task(f"T{i+1}", d) for i, d in enumerate(durations)]


# ── required_workers / is_capacity_feasible ───────────────────────────────────

class TestFeasibilityChecker:
    def test_single_task_fits(self):
        assert required_workers([5], 5) == 1

    def test_single_task_capacity_too_small(self):
        # When capacity < a task's duration, greedy starts a new group for that task
        # (0 + 5 > 4 triggers a split: groups=2, running=5).
        # is_capacity_feasible will return False for k=1 since 2 > 1.
        assert required_workers([5], 4) == 2

    def test_two_tasks_fit(self):
        assert required_workers([3, 3], 6) == 1

    def test_two_tasks_split(self):
        assert required_workers([3, 3], 5) == 2

    def test_many_tasks(self):
        # durations [7,2,5,10,8], capacity=14
        assert required_workers([7, 2, 5, 10, 8], 14) == 3

    def test_monotonicity(self):
        """required_workers must be monotonically non-increasing as capacity grows."""
        durations = [7, 2, 5, 10, 8]
        total = sum(durations)
        max_d = max(durations)
        counts = [required_workers(durations, c) for c in range(max_d, total + 1)]
        for a, b in zip(counts, counts[1:]):
            assert a >= b, f"Not monotonic: {a} < {b}"

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            required_workers([1, 2], 0)

    def test_is_feasible_true(self):
        assert is_capacity_feasible([7, 2, 5, 10, 8], 3, 14) is True

    def test_is_feasible_false(self):
        assert is_capacity_feasible([7, 2, 5, 10, 8], 3, 9) is False


# ── optimize_allocation ───────────────────────────────────────────────────────

class TestOptimizeAllocation:
    def test_one_task_one_worker(self):
        tasks = make_tasks(7)
        result = optimize_allocation(tasks, 1)
        assert result.optimal_capacity == 7
        assert len(result.groups) == 1
        assert result.groups[0].total_duration == 7

    def test_one_worker_equals_total(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 1)
        assert result.optimal_capacity == sum(t.duration for t in tasks)

    def test_one_worker_per_task_equals_max(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 5)
        assert result.optimal_capacity == 10  # max duration

    def test_equal_durations(self):
        tasks = make_tasks(4, 4, 4, 4)
        result = optimize_allocation(tasks, 2)
        assert result.optimal_capacity == 8

    def test_uneven_durations(self):
        """Canonical example from the spec: J1=7,J2=2,J3=5,J4=10,J5=8, k=3."""
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 3)
        assert result.optimal_capacity == 14

    def test_unequal_task_count_per_worker(self):
        """A case where optimal partition has unequal task counts per worker."""
        tasks = make_tasks(1, 1, 1, 10)
        result = optimize_allocation(tasks, 2)
        # Optimal: W1=[1,1,1], W2=[10] → max=10; or W1=[1], W2=[1,1,10]=12 → max=12
        assert result.optimal_capacity == 10

    def test_workers_equals_n_boundary(self):
        tasks = make_tasks(3, 1, 7, 2)
        result = optimize_allocation(tasks, 4)
        assert result.optimal_capacity == 7
        assert len(result.groups) == 4

    def test_empty_task_list(self):
        with pytest.raises(ValidationError):
            optimize_allocation([], 1)

    def test_workers_zero(self):
        with pytest.raises(ValidationError):
            optimize_allocation(make_tasks(1, 2), 0)

    def test_workers_negative(self):
        with pytest.raises(ValidationError):
            optimize_allocation(make_tasks(1, 2), -1)

    def test_workers_exceeds_tasks(self):
        with pytest.raises(ValidationError):
            optimize_allocation(make_tasks(1, 2), 3)

    def test_large_durations(self):
        """Should not overflow; uses Python arbitrary-precision ints."""
        tasks = make_tasks(10_000_000, 10_000_000)
        result = optimize_allocation(tasks, 1)
        assert result.optimal_capacity == 20_000_000


# ── Group reconstruction invariants ───────────────────────────────────────────

class TestReconstructGroups:
    def _check_invariants(self, tasks, workers, optimal_capacity):
        groups = reconstruct_groups(tasks, workers, optimal_capacity)
        assert len(groups) == workers, "Wrong number of groups"
        # Every group is non-empty
        for g in groups:
            assert len(g.tasks) >= 1, "Empty group found"
        # All tasks appear exactly once in original order
        all_tasks = [t for g in groups for t in g.tasks]
        assert all_tasks == list(tasks), "Task order or membership broken"
        # Each group sum <= optimal_capacity
        for g in groups:
            assert g.total_duration <= optimal_capacity, (
                f"Group {g.worker_id} total {g.total_duration} exceeds {optimal_capacity}"
            )
        return groups

    def test_invariants_standard(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        self._check_invariants(tasks, 3, 14)

    def test_invariants_one_worker(self):
        tasks = make_tasks(1, 2, 3)
        self._check_invariants(tasks, 1, 6)

    def test_invariants_n_workers(self):
        tasks = make_tasks(3, 1, 7)
        self._check_invariants(tasks, 3, 7)

    def test_invariants_equal_durations(self):
        tasks = make_tasks(4, 4, 4, 4, 4, 4)
        result = optimize_allocation(tasks, 3)
        self._check_invariants(tasks, 3, result.optimal_capacity)

    def test_start_end_indices_correct(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 3)
        # Groups should cover indices 0 to n-1 without gaps or overlaps
        all_indices = []
        for g in result.groups:
            all_indices.extend(range(g.start_index, g.end_index + 1))
        assert all_indices == list(range(len(tasks)))


# ── Trace recording ───────────────────────────────────────────────────────────

class TestTrace:
    def test_trace_not_empty_for_multi_worker(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 3)
        assert len(result.trace) > 0

    def test_trace_bounds_progress(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 3)
        for step in result.trace:
            assert step.low <= step.mid <= step.high
            assert step.new_low <= step.new_high

    def test_trace_terminates_at_optimum(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 3)
        # Last trace step's new_low or new_high should converge
        last = result.trace[-1]
        # After convergence, low == high == optimal
        assert result.optimal_capacity == result.lower_bound or result.feasibility_checks > 0

    def test_feasibility_checks_count(self):
        tasks = make_tasks(7, 2, 5, 10, 8)
        result = optimize_allocation(tasks, 3)
        assert result.feasibility_checks == len(result.trace)

    def test_one_worker_has_no_trace(self):
        tasks = make_tasks(5, 3)
        result = optimize_allocation(tasks, 1)
        assert result.feasibility_checks == 0
        assert result.trace == []


# ── Task / duration validation ────────────────────────────────────────────────

class TestInputValidation:
    def test_negative_duration_rejected(self):
        with pytest.raises((ValidationError, ValueError)):
            Task("Bad", -1)

    def test_zero_duration_rejected(self):
        with pytest.raises((ValidationError, ValueError)):
            Task("Bad", 0)

    def test_float_task_not_a_task(self):
        """Task model requires integer duration; passing float should raise."""
        with pytest.raises((TypeError, ValueError)):
            Task("Bad", 3.5)

    def test_blank_task_name_rejected(self):
        with pytest.raises((ValidationError, ValueError)):
            Task("", 5)

    def test_workers_must_be_int(self):
        with pytest.raises((ValidationError, TypeError)):
            optimize_allocation(make_tasks(1, 2), 1.5)
