"""Workload allocation algorithm for LoadLens.

Core algorithm: binary-search-on-answer combined with a greedy feasibility
checker. No Streamlit, SQLite, or UI dependency.

Algorithm overview
------------------
Given `n` tasks with positive integer durations d[0..n-1] and `k` workers:

1. **Lower bound**: max(max(d), ceil(sum(d)/k)).
   - No valid capacity can be smaller than the largest single task (a task
     is indivisible and must fit in exactly one worker's group).
   - No valid capacity can be smaller than the average workload per worker
     (if every worker had less than ceil(total/k), the combined sum would
     fall short of total).

2. **Upper bound**: sum(d).
   - One worker can always hold all tasks; this is trivially feasible.

3. **Feasibility check** (O(n)):
   - Scan tasks left-to-right, greedily starting a new group whenever the
     current group would exceed capacity C. Count the groups.
   - A capacity C is *feasible* if the greedy count <= k.

4. **Monotonicity** (why binary search works):
   - Durations are strictly positive, so increasing C can only merge adjacent
     groups (never require a new split). The feasibility predicate transitions
     from False to True exactly once as C increases. Binary search on a
     monotonic predicate is valid.

5. **Binary search** (O(n log R), R = upper - lower):
   - Standard left-boundary binary search: maintain [low, high] where
     high is always feasible. Shrink the interval until low == high.

6. **Group reconstruction** (O(n)):
   - With optimal capacity opt, place splits greedily. If the greedy pass
     uses fewer than k groups (can happen when capacity is loose), distribute
     remaining splits by subdividing the largest groups, keeping order and
     ensuring every sub-group is non-empty.

Time complexity : O(n log R)  where R = sum(d) - lower_bound + 1
Space complexity: O(n)  for the trace list (O(log R) entries, each O(1) fields)
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from loadlens.models import (
    AllocationResult,
    BinarySearchStep,
    Task,
    WorkerGroup,
)
from loadlens.validation import ValidationError, validate_tasks, validate_worker_count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def required_workers(durations: Sequence[int], capacity: int) -> int:
    """Return the minimum number of contiguous groups needed under *capacity*.

    Greedy left-to-right scan: keep adding tasks to the current group while
    the running sum stays within *capacity*; start a new group when it would
    exceed the limit.

    Invariants:
    - All durations are positive integers.
    - capacity >= max(durations) is required for a valid result; if capacity
      is smaller than some duration, this function may return a count that is
      larger than n (infeasible, correctly indicated by a high count).

    Args:
        durations: Ordered sequence of positive integer task durations.
        capacity: Candidate maximum workload per worker (positive integer).

    Returns:
        Minimum number of groups (always >= 1).

    Raises:
        ValueError: If capacity is not a positive integer.
    """
    if capacity <= 0:
        raise ValueError(f"capacity must be positive, got {capacity}.")
    groups = 1
    running = 0
    for d in durations:
        if running + d > capacity:
            groups += 1
            running = d
        else:
            running += d
    return groups


def is_capacity_feasible(durations: Sequence[int], workers: int, capacity: int) -> bool:
    """Return True if *capacity* allows an allocation with at most *workers* groups.

    Args:
        durations: Ordered sequence of positive integer task durations.
        workers: Maximum allowed groups.
        capacity: Candidate capacity.

    Returns:
        True if required_workers(durations, capacity) <= workers.
    """
    return required_workers(durations, capacity) <= workers


def optimize_allocation(tasks: Sequence[Task], workers: int) -> AllocationResult:
    """Find the allocation that minimises the maximum worker workload.

    This is the main entry point. Validates inputs, runs binary search,
    reconstructs groups, and returns a fully populated AllocationResult.

    Algorithm complexity: O(n log R) time, O(n) auxiliary space.

    Args:
        tasks: Ordered sequence of Task objects (validated before search).
        workers: Number of workers; must satisfy 1 <= workers <= len(tasks).

    Returns:
        AllocationResult with optimal capacity, exact k groups, and trace.

    Raises:
        ValidationError: If tasks or workers are invalid.
    """
    validated_tasks = validate_tasks(tasks)
    validated_workers = validate_worker_count(workers, validated_tasks)

    durations = [t.duration for t in validated_tasks]
    total = sum(durations)
    max_d = max(durations)

    lower_bound = max(max_d, math.ceil(total / validated_workers))
    upper_bound = total

    # Edge case: 1 worker or workers == n (every task alone)
    # Binary search still handles these correctly, but short-circuit for speed.
    if validated_workers == 1:
        opt = total
        groups = reconstruct_groups(validated_tasks, validated_workers, opt)
        return AllocationResult(
            tasks=list(validated_tasks),
            workers=validated_workers,
            optimal_capacity=opt,
            groups=groups,
            total_duration=total,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            feasibility_checks=0,
            trace=[],
        )

    trace: List[BinarySearchStep] = []
    low, high = lower_bound, upper_bound

    # Binary search: find the smallest C such that is_capacity_feasible(C) is True.
    # Invariant: high is always feasible.
    while low < high:
        mid = (low + high) // 2
        req = required_workers(durations, mid)
        feasible = req <= validated_workers

        step = BinarySearchStep(
            low=low,
            high=high,
            mid=mid,
            required_workers=req,
            feasible=feasible,
            new_low=mid + 1 if not feasible else low,
            new_high=mid if feasible else high,
        )
        trace.append(step)

        if feasible:
            high = mid
        else:
            low = mid + 1

    opt = low
    groups = reconstruct_groups(validated_tasks, validated_workers, opt)

    return AllocationResult(
        tasks=list(validated_tasks),
        workers=validated_workers,
        optimal_capacity=opt,
        groups=groups,
        total_duration=total,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        feasibility_checks=len(trace),
        trace=trace,
    )


def reconstruct_groups(
    tasks: Sequence[Task], workers: int, optimal_capacity: int
) -> List[WorkerGroup]:
    """Build exactly *workers* non-empty contiguous groups.

    Step 1 — greedy forward scan with capacity limit.
    Step 2 — if greedy produced fewer groups than workers (possible when
    optimal_capacity >= sum / workers is slack), subdivide the largest groups
    by inserting additional splits while keeping every group non-empty and
    preserving task order.

    Args:
        tasks: Ordered tasks.
        workers: Exact number of groups required.
        optimal_capacity: Maximum allowed sum per group.

    Returns:
        Exactly *workers* WorkerGroup objects, covering all tasks once in order.

    Raises:
        ValueError: If reconstruction is arithmetically impossible (should not
            occur for valid inputs after optimization).
    """
    task_list = list(tasks)
    n = len(task_list)

    # --- Step 1: greedy split ---
    raw_groups: List[List[int]] = []  # list of task-index lists
    current: List[int] = []
    running = 0
    for i, t in enumerate(task_list):
        if current and running + t.duration > optimal_capacity:
            raw_groups.append(current)
            current = [i]
            running = t.duration
        else:
            current.append(i)
            running += t.duration
    if current:
        raw_groups.append(current)

    # --- Step 2: add missing splits when greedy used fewer groups ---
    # Each group index list can be split by inserting a split point anywhere
    # between two adjacent tasks. We repeat until we have exactly k groups,
    # always splitting the current largest-sum group that has >= 2 tasks.
    while len(raw_groups) < workers:
        # Find the group with largest total that has at least 2 tasks.
        best_gi = -1
        best_sum = -1
        for gi, idxs in enumerate(raw_groups):
            if len(idxs) >= 2:
                s = sum(task_list[i].duration for i in idxs)
                if s > best_sum:
                    best_sum = s
                    best_gi = gi
        if best_gi == -1:
            # Cannot split further (every group is already a single task)
            raise ValueError(
                "Cannot create the requested number of non-empty groups; "
                "this suggests a workers > n violation that should have been "
                "caught earlier."
            )
        # Split the chosen group at the midpoint (preserves order, keeps non-empty)
        idxs = raw_groups[best_gi]
        mid_point = len(idxs) // 2
        left = idxs[:mid_point]
        right = idxs[mid_point:]
        raw_groups = raw_groups[:best_gi] + [left, right] + raw_groups[best_gi + 1 :]

    # Build typed WorkerGroup objects
    groups: List[WorkerGroup] = []
    for wid, idxs in enumerate(raw_groups, start=1):
        group_tasks = [task_list[i] for i in idxs]
        groups.append(
            WorkerGroup(
                worker_id=wid,
                tasks=group_tasks,
                total_duration=sum(t.duration for t in group_tasks),
                start_index=idxs[0],
                end_index=idxs[-1],
            )
        )
    return groups
