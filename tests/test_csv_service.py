"""Tests for the CSV import/export service."""

from __future__ import annotations

import pytest

from loadlens.services.csv_service import (
    generate_allocation_csv,
    parse_csv_tasks,
    tasks_to_csv,
)
from loadlens.algorithms.allocation import optimize_allocation
from loadlens.models import Task
from loadlens.validation import ValidationError, MAX_CSV_BYTES, MAX_TASKS


def _encode(s: str) -> bytes:
    return s.encode("utf-8")


# ── parse_csv_tasks ───────────────────────────────────────────────────────────

class TestParseCsvTasks:
    def test_valid_csv(self):
        csv = "task_name,duration\nTask A,5\nTask B,10\n"
        tasks = parse_csv_tasks(_encode(csv))
        assert len(tasks) == 2
        assert tasks[0].name == "Task A"
        assert tasks[0].duration == 5
        assert tasks[1].name == "Task B"
        assert tasks[1].duration == 10

    def test_unicode_names(self):
        csv = "task_name,duration\n日本語タスク,7\nTâche française,3\n"
        tasks = parse_csv_tasks(_encode(csv))
        assert tasks[0].name == "日本語タスク"
        assert tasks[1].name == "Tâche française"

    def test_missing_duration_header(self):
        csv = "task_name,time\nA,5\n"
        with pytest.raises(ValidationError, match="missing"):
            parse_csv_tasks(_encode(csv))

    def test_missing_name_header(self):
        csv = "name,duration\nA,5\n"
        with pytest.raises(ValidationError, match="missing"):
            parse_csv_tasks(_encode(csv))

    def test_empty_file(self):
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode(""))

    def test_header_only(self):
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode("task_name,duration\n"))

    def test_negative_duration(self):
        csv = "task_name,duration\nA,-5\n"
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode(csv))

    def test_zero_duration(self):
        csv = "task_name,duration\nA,0\n"
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode(csv))

    def test_decimal_duration(self):
        csv = "task_name,duration\nA,3.5\n"
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode(csv))

    def test_blank_duration(self):
        csv = "task_name,duration\nA,\n"
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode(csv))

    def test_blank_task_name(self):
        csv = "task_name,duration\n,5\n"
        with pytest.raises(ValidationError):
            parse_csv_tasks(_encode(csv))

    def test_file_too_large(self):
        # Construct content just over 5 MB
        big = ("task_name,duration\n" + "A,1\n" * 100).encode()
        small_limit = len(big) - 1
        with pytest.raises(ValidationError, match="bytes"):
            parse_csv_tasks(big, max_bytes=small_limit)

    def test_row_limit(self):
        rows = "task_name,duration\n" + "".join(f"T{i},1\n" for i in range(20))
        with pytest.raises(ValidationError, match="rows"):
            parse_csv_tasks(_encode(rows), max_rows=10)

    def test_bom_stripped(self):
        """Excel-exported UTF-8 BOM should be handled."""
        # Encode with utf-8-sig to produce a real BOM-prefixed file (as Excel does).
        # The string itself should NOT start with \ufeff to avoid double-BOM.
        csv = "task_name,duration\nA,5\n"
        tasks = parse_csv_tasks(csv.encode("utf-8-sig"))
        assert tasks[0].name == "A"

    def test_case_insensitive_headers(self):
        csv = "Task_Name,Duration\nA,3\n"
        tasks = parse_csv_tasks(_encode(csv))
        assert tasks[0].duration == 3

    def test_order_preserved(self):
        csv = "task_name,duration\nC,3\nA,1\nB,2\n"
        tasks = parse_csv_tasks(_encode(csv))
        assert [t.name for t in tasks] == ["C", "A", "B"]


# ── generate_allocation_csv ───────────────────────────────────────────────────

class TestGenerateAllocationCsv:
    def _make_result(self):
        tasks = [Task(f"T{i+1}", d) for i, d in enumerate([7, 2, 5, 10, 8])]
        return optimize_allocation(tasks, 3)

    def test_csv_has_header(self):
        result = self._make_result()
        csv = generate_allocation_csv(result)
        assert csv.startswith("worker_id")

    def test_csv_row_count(self):
        result = self._make_result()
        csv = generate_allocation_csv(result)
        lines = [l for l in csv.strip().splitlines() if l]
        # 1 header + 5 task rows
        assert len(lines) == 6

    def test_optimal_capacity_in_every_row(self):
        result = self._make_result()
        csv = generate_allocation_csv(result)
        data_lines = csv.strip().splitlines()[1:]
        for line in data_lines:
            assert str(result.optimal_capacity) in line

    def test_formula_injection_escaping(self):
        from loadlens.validation import sanitize_task_name_for_csv
        assert sanitize_task_name_for_csv("=SUM(A1)").startswith("'")
        assert sanitize_task_name_for_csv("+1").startswith("'")
        assert sanitize_task_name_for_csv("-1").startswith("'")
        assert sanitize_task_name_for_csv("@user").startswith("'")
        assert sanitize_task_name_for_csv("Normal Task") == "Normal Task"

    def test_unit_label_in_header(self):
        result = self._make_result()
        csv = generate_allocation_csv(result, unit="minutes")
        assert "minutes" in csv.splitlines()[0]


# ── tasks_to_csv ──────────────────────────────────────────────────────────────

class TestTasksToCsv:
    def test_roundtrip(self):
        tasks = [Task("Alpha", 5), Task("Beta", 3)]
        csv_str = tasks_to_csv(tasks)
        recovered = parse_csv_tasks(csv_str.encode())
        assert [(t.name, t.duration) for t in recovered] == [
            ("Alpha", 5), ("Beta", 3)
        ]
