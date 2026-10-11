"""CSV import/export service for LoadLens.

Handles safe parsing of uploaded CSV data and generation of allocation
export files. Uses only the Python standard library (csv module).

Security notes
--------------
- Uploaded data is treated as untrusted text; no eval/exec is performed.
- Column values are never used to construct SQL queries.
- Task names leading with formula-injection characters (=, +, -, @)
  are prefixed with a single quote in exported CSV files.
- File size and row count are enforced here (domain boundary), not only
  in UI widgets.

CSV Schema
----------
Input:  task_name,duration   (header required, case-insensitive)
Output: worker_id,worker_workload,task_order,task_name,task_duration,optimal_capacity
"""

from __future__ import annotations

import csv
import io
from typing import List, Optional, Tuple

from loadlens.models import AllocationResult, Task, WorkerGroup
from loadlens.validation import (
    MAX_CSV_BYTES,
    MAX_TASKS,
    ValidationError,
    parse_duration,
    sanitize_task_name_for_csv,
)

# Required CSV column names (case-insensitive match)
REQUIRED_HEADERS = {"task_name", "duration"}


def parse_csv_tasks(
    content: bytes,
    *,
    max_bytes: int = MAX_CSV_BYTES,
    max_rows: int = MAX_TASKS,
) -> List[Task]:
    """Parse uploaded CSV bytes into an ordered list of Task objects.

    Args:
        content: Raw bytes from an uploaded file.
        max_bytes: Maximum allowed file size in bytes.
        max_rows: Maximum allowed number of data rows (excluding header).

    Returns:
        Ordered list of Task objects.

    Raises:
        ValidationError: On any structural or data issue.
    """
    if len(content) > max_bytes:
        raise ValidationError(
            f"Uploaded file is {len(content):,} bytes; the maximum allowed is "
            f"{max_bytes:,} bytes ({max_bytes // (1024 * 1024)} MB)."
        )

    try:
        text = content.decode("utf-8-sig")  # Handle BOM from Excel exports
    except UnicodeDecodeError:
        raise ValidationError(
            "Could not decode the file as UTF-8. Please save the CSV with UTF-8 encoding."
        )

    reader = csv.DictReader(io.StringIO(text))

    # Validate headers
    if reader.fieldnames is None:
        raise ValidationError("The CSV file appears to be empty or has no header row.")

    normalized_headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = REQUIRED_HEADERS - normalized_headers
    if missing:
        raise ValidationError(
            f"CSV is missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected headers: task_name,duration"
        )

    # Check for ambiguous/duplicate required headers
    raw_lower = [h.strip().lower() for h in reader.fieldnames if h]
    for req in REQUIRED_HEADERS:
        if raw_lower.count(req) > 1:
            raise ValidationError(
                f"Column '{req}' appears more than once in the CSV header. "
                "Please use unambiguous column names."
            )

    tasks: List[Task] = []
    errors: List[str] = []

    for row_num, row in enumerate(reader, start=2):  # start=2 because header is row 1
        if row_num - 1 > max_rows:
            raise ValidationError(
                f"Too many rows: exceeded the maximum of {max_rows} data rows. "
                "Please reduce the file size."
            )

        # Normalize keys
        normalized_row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}

        raw_name = normalized_row.get("task_name", "").strip()
        raw_duration = normalized_row.get("duration", "").strip()

        if not raw_name:
            errors.append(f"Row {row_num}: task_name is blank.")
            continue

        try:
            duration = parse_duration(raw_duration, row_num)
        except ValidationError as e:
            errors.append(str(e))
            continue

        tasks.append(Task(name=raw_name, duration=duration))

    if errors:
        raise ValidationError(
            "CSV contained invalid rows:\n" + "\n".join(f"  • {e}" for e in errors)
        )

    if not tasks:
        raise ValidationError(
            "No valid tasks found in the CSV file. "
            "Ensure the file has at least one data row after the header."
        )

    return tasks


def generate_allocation_csv(result: AllocationResult, unit: str = "units") -> str:
    """Generate a CSV export string from an AllocationResult.

    Output columns: worker_id, worker_workload, task_order, task_name,
                    task_duration, optimal_capacity.

    Task names leading with formula-injection characters are escaped.

    Args:
        result: A completed AllocationResult.
        unit: Display unit label appended to numeric column headers.

    Returns:
        UTF-8 CSV string (with header row).
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    header = [
        "worker_id",
        f"worker_workload_{unit}",
        "task_order",
        "task_name",
        f"task_duration_{unit}",
        f"optimal_capacity_{unit}",
    ]
    writer.writerow(header)

    task_order = 1
    for group in result.groups:
        for task in group.tasks:
            writer.writerow([
                group.worker_id,
                group.total_duration,
                task_order,
                sanitize_task_name_for_csv(task.name),
                task.duration,
                result.optimal_capacity,
            ])
            task_order += 1

    return output.getvalue()


def tasks_to_csv(tasks: List[Task]) -> str:
    """Serialize a task list to the standard LoadLens CSV schema.

    Useful for saving a scenario's task list for later re-import.

    Args:
        tasks: Ordered list of Task objects.

    Returns:
        UTF-8 CSV string with header task_name,duration.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["task_name", "duration"])
    for task in tasks:
        writer.writerow([sanitize_task_name_for_csv(task.name), task.duration])
    return output.getvalue()
