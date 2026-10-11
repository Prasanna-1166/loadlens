"""Domain models for LoadLens.

All data is immutable and typed. No Streamlit or SQLite dependency here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Task:
    """A single indivisible job with an ordered name and positive integer duration.

    Attributes:
        name: Human-readable task identifier (may contain Unicode).
        duration: Positive integer processing time in chosen units.
    """

    name: str
    duration: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Task name must be a non-empty string.")
        if not isinstance(self.duration, int) or self.duration <= 0:
            raise ValueError(
                f"Task '{self.name}' duration must be a positive integer, got {self.duration!r}."
            )


@dataclass(frozen=True)
class WorkerGroup:
    """A contiguous block of tasks assigned to one worker.

    Attributes:
        worker_id: 1-based integer worker identifier.
        tasks: Ordered list of tasks in this group (preserves input order).
        total_duration: Sum of task durations in this group.
        start_index: 0-based index of the first task in the global task list.
        end_index: 0-based index of the last task in the global task list (inclusive).
    """

    worker_id: int
    tasks: List[Task]
    total_duration: int
    start_index: int
    end_index: int

    def headroom(self, capacity: int) -> int:
        """Unused capacity for this worker."""
        return capacity - self.total_duration

    def utilization_pct(self, capacity: int) -> float:
        """Percentage of capacity used; returns 0.0 if capacity is 0."""
        if capacity <= 0:
            return 0.0
        return 100.0 * self.total_duration / capacity


@dataclass(frozen=True)
class BinarySearchStep:
    """One iteration of the binary-search feasibility sweep.

    Attributes:
        low: Lower bound (inclusive) at the start of this iteration.
        high: Upper bound (inclusive) at the start of this iteration.
        mid: Candidate capacity tested.
        required_workers: Greedy minimum workers needed under capacity=mid.
        feasible: True if required_workers <= k.
        new_low: Updated lower bound after this step.
        new_high: Updated upper bound after this step.
    """

    low: int
    high: int
    mid: int
    required_workers: int
    feasible: bool
    new_low: int
    new_high: int


@dataclass(frozen=True)
class AllocationResult:
    """Complete result of the workload allocation optimization.

    Attributes:
        tasks: Input tasks in original order.
        workers: Number of requested workers.
        optimal_capacity: Minimum feasible maximum workload.
        groups: Exactly `workers` contiguous non-empty WorkerGroup objects.
        total_duration: Sum of all task durations.
        lower_bound: Theoretical lower bound used for the search.
        upper_bound: Theoretical upper bound (sum of durations).
        feasibility_checks: Number of binary-search iterations performed.
        trace: Ordered list of binary-search steps.
    """

    tasks: List[Task]
    workers: int
    optimal_capacity: int
    groups: List[WorkerGroup]
    total_duration: int
    lower_bound: int
    upper_bound: int
    feasibility_checks: int
    trace: List[BinarySearchStep] = field(default_factory=list)

    @property
    def max_task_duration(self) -> int:
        """Largest individual task duration."""
        return max(t.duration for t in self.tasks)

    @property
    def theoretical_lower_bound(self) -> int:
        """max(max_task_duration, ceil(total/workers))."""
        return max(self.max_task_duration, math.ceil(self.total_duration / self.workers))


@dataclass
class RotatedSearchResult:
    """Result of a rotated-array binary search.

    Attributes:
        array: The rotated array that was searched.
        target: The search target.
        index: Zero-based index if found, or -1 if not found.
        found: True if the target was found.
        trace: Ordered list of (low, mid, high, half_chosen) dicts.
    """

    array: List[int]
    target: int
    index: int
    found: bool
    trace: List[dict] = field(default_factory=list)


@dataclass
class ScenarioRecord:
    """A saved scenario stored in the local SQLite database.

    Attributes:
        scenario_id: Auto-assigned integer primary key (None before insert).
        name: User-provided scenario name.
        created_at: ISO-8601 timestamp string.
        tasks: Ordered list of tasks.
        workers: Number of workers.
        optimal_capacity: Stored optimum from the solver.
        groups_json: JSON-serialized allocation groups for display.
        algorithm_version: String label, e.g. "binary_search_v1".
        schema_version: Integer for forward-compatible migration.
    """

    name: str
    created_at: str
    tasks: List[Task]
    workers: int
    optimal_capacity: int
    groups_json: str
    algorithm_version: str = "binary_search_v1"
    schema_version: int = 1
    scenario_id: Optional[int] = None
