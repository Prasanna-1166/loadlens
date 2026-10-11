"""Tests for the SQLite scenario repository."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from loadlens.models import ScenarioRecord, Task
from loadlens.persistence.scenario_repository import PersistenceError, ScenarioRepository


def _temp_repo() -> ScenarioRepository:
    """Create a repository backed by a temp in-memory-like file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return ScenarioRepository(db_path=Path(tmp.name))


def _sample_record(name: str = "Test Scenario") -> ScenarioRecord:
    tasks = [Task("Alpha", 5), Task("Beta", 10), Task("Gamma", 3)]
    groups_json = json.dumps([
        {"worker_id": 1, "tasks": [{"name": "Alpha", "duration": 5}], "total_duration": 5},
        {"worker_id": 2, "tasks": [{"name": "Beta", "duration": 10}, {"name": "Gamma", "duration": 3}], "total_duration": 13},
    ])
    return ScenarioRecord(
        name=name,
        created_at="",
        tasks=tasks,
        workers=2,
        optimal_capacity=13,
        groups_json=groups_json,
    )


class TestScenarioRepository:
    def test_save_and_list(self):
        repo = _temp_repo()
        record = _sample_record("My Scenario")
        saved = repo.save(record)
        assert saved.scenario_id is not None
        assert saved.name == "My Scenario"
        all_records = repo.list_all()
        assert len(all_records) == 1
        assert all_records[0].name == "My Scenario"

    def test_save_assigns_timestamp(self):
        repo = _temp_repo()
        saved = repo.save(_sample_record())
        assert saved.created_at != ""
        assert "T" in saved.created_at  # ISO format

    def test_get_by_id(self):
        repo = _temp_repo()
        saved = repo.save(_sample_record("FindMe"))
        fetched = repo.get_by_id(saved.scenario_id)
        assert fetched is not None
        assert fetched.name == "FindMe"
        assert len(fetched.tasks) == 3

    def test_get_by_id_not_found(self):
        repo = _temp_repo()
        result = repo.get_by_id(999_999)
        assert result is None

    def test_delete(self):
        repo = _temp_repo()
        saved = repo.save(_sample_record())
        deleted = repo.delete(saved.scenario_id)
        assert deleted is True
        assert repo.get_by_id(saved.scenario_id) is None

    def test_delete_nonexistent(self):
        repo = _temp_repo()
        result = repo.delete(999_999)
        assert result is False

    def test_list_newest_first(self):
        repo = _temp_repo()
        s1 = repo.save(_sample_record("First"))
        s2 = repo.save(_sample_record("Second"))
        s3 = repo.save(_sample_record("Third"))
        all_rec = repo.list_all()
        names = [r.name for r in all_rec]
        assert names == ["Third", "Second", "First"]

    def test_task_order_preserved(self):
        repo = _temp_repo()
        tasks = [Task(f"Step{i}", i + 1) for i in range(5)]
        record = ScenarioRecord(
            name="Order Test",
            created_at="",
            tasks=tasks,
            workers=2,
            optimal_capacity=10,
            groups_json="[]",
        )
        saved = repo.save(record)
        fetched = repo.get_by_id(saved.scenario_id)
        assert [(t.name, t.duration) for t in fetched.tasks] == [
            ("Step0", 1), ("Step1", 2), ("Step2", 3), ("Step3", 4), ("Step4", 5)
        ]

    def test_multiple_saves_independent(self):
        repo = _temp_repo()
        repo.save(_sample_record("A"))
        repo.save(_sample_record("B"))
        repo.save(_sample_record("C"))
        assert len(repo.list_all()) == 3

    def test_workers_and_capacity_stored(self):
        repo = _temp_repo()
        saved = repo.save(_sample_record())
        fetched = repo.get_by_id(saved.scenario_id)
        assert fetched.workers == 2
        assert fetched.optimal_capacity == 13

    def test_invalid_db_path_raises_persistence_error(self):
        """A path that cannot be created should raise PersistenceError."""
        bad_path = Path("/nonexistent_dir_xyz/loadlens.db")
        repo = ScenarioRepository(db_path=bad_path)
        with pytest.raises(PersistenceError):
            repo._ensure_initialized()

    def test_persistence_error_does_not_affect_algorithm(self):
        """Verify PersistenceError can be caught without affecting other code."""
        bad_repo = ScenarioRepository(db_path=Path("/nonexistent/db.db"))
        try:
            bad_repo.list_all()
        except PersistenceError:
            pass  # Expected; the algorithm layer should not be affected

        # Algorithm works independently
        from loadlens.algorithms.allocation import optimize_allocation
        tasks = [Task("A", 5), Task("B", 10)]
        result = optimize_allocation(tasks, 2)
        assert result.optimal_capacity == 10
