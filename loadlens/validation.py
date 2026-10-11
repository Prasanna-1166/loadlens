"""Input validation for LoadLens.

Validates tasks and worker counts before handing off to the algorithm layer.
All raised exceptions use ValueError with user-readable messages.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from loadlens.models import Task

# Safety limits
MAX_TASKS: int = 10_000
MAX_CSV_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_DURATION: int = 10_000_000  # prevent integer overflow in feasibility checks


class ValidationError(ValueError):
    """Raised when user-supplied data is invalid."""


def validate_tasks(tasks: Sequence[Task]) -> List[Task]:
    """Validate a sequence of tasks and return a clean list.

    Rules:
    - Must be non-empty.
    - At most MAX_TASKS tasks.
    - Each task name must be a non-empty string.
    - Each duration must be a positive integer <= MAX_DURATION.
    - Order is always preserved exactly.

    Args:
        tasks: Sequence of Task objects to validate.

    Returns:
        Validated list of Task objects in original order.

    Raises:
        ValidationError: If any rule is violated.
    """
    if not tasks:
        raise ValidationError("Task list must not be empty.")
    if len(tasks) > MAX_TASKS:
        raise ValidationError(
            f"Too many tasks: {len(tasks)} exceeds the maximum of {MAX_TASKS}."
        )
    validated: List[Task] = []
    for i, task in enumerate(tasks):
        if not isinstance(task, Task):
            raise ValidationError(f"Row {i + 1}: expected a Task object, got {type(task).__name__}.")
        if task.duration > MAX_DURATION:
            raise ValidationError(
                f"Row {i + 1}: duration {task.duration} exceeds the maximum of {MAX_DURATION}."
            )
        validated.append(task)
    return validated


def validate_worker_count(workers: int, tasks: Sequence[Task]) -> int:
    """Validate the requested number of workers.

    Rules:
    - Must be a positive integer.
    - Must be <= number of tasks (each worker must get at least one task).

    Args:
        workers: Requested worker count.
        tasks: The validated task list.

    Returns:
        Validated worker count.

    Raises:
        ValidationError: If the worker count is invalid.
    """
    if not isinstance(workers, int) or isinstance(workers, bool):
        raise ValidationError(f"Worker count must be an integer, got {type(workers).__name__}.")
    if workers < 1:
        raise ValidationError(f"Worker count must be at least 1, got {workers}.")
    n = len(tasks)
    if workers > n:
        raise ValidationError(
            f"Worker count ({workers}) cannot exceed the number of tasks ({n})."
        )
    return workers


def parse_duration(value: str, row_num: int) -> int:
    """Parse a string into a positive integer duration.

    Args:
        value: Raw string from CSV or UI input.
        row_num: 1-based row number for error messages.

    Returns:
        Positive integer duration.

    Raises:
        ValidationError: If the value is not a valid positive integer.
    """
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        raise ValidationError(f"Row {row_num}: duration is blank.")
    # Reject floats explicitly (e.g. "3.5")
    if "." in value:
        raise ValidationError(
            f"Row {row_num}: duration '{value}' is a decimal. Only positive integers are accepted."
        )
    try:
        int_val = int(value)
    except ValueError:
        raise ValidationError(
            f"Row {row_num}: '{value}' is not a valid integer duration."
        )
    if int_val <= 0:
        raise ValidationError(
            f"Row {row_num}: duration must be a positive integer, got {int_val}."
        )
    if int_val > MAX_DURATION:
        raise ValidationError(
            f"Row {row_num}: duration {int_val} exceeds the maximum of {MAX_DURATION}."
        )
    return int_val


def sanitize_task_name_for_csv(name: str) -> str:
    """Escape spreadsheet-formula-injection characters at the start of a task name.

    Leading '=', '+', '-', '@', TAB, CR are prefixed with a single quote
    to prevent formula injection in spreadsheet applications.

    Args:
        name: Raw task name string.

    Returns:
        Safe task name for CSV export.
    """
    if name and name[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + name
    return name
