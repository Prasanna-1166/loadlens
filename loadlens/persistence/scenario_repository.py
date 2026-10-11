"""SQLite scenario repository for LoadLens.

Provides local scenario persistence using Python's built-in sqlite3 module.
No external database account or credentials are required.

Design notes
------------
- Database file is stored in a platform-independent local-data directory
  (see _db_path()). Generated database files must be added to .gitignore.
- All SQL uses parameterized queries; no user data is string-interpolated
  into SQL.
- Tables are created safely with CREATE TABLE IF NOT EXISTS on startup.
- Persistence failures are reported as PersistenceError and must NOT crash
  the core optimization planner.
- JSON is used for serializing task lists and allocation groups; no pickle
  is ever used.
- This is local-first storage. A hosted app's ephemeral filesystem may not
  persist data across restarts; the UI should document this caveat clearly.

Schema version: 1
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

from loadlens.models import ScenarioRecord, Task

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
ALGORITHM_VERSION = "binary_search_v1"

_DDL = """
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    created_at        TEXT    NOT NULL,
    tasks_json        TEXT    NOT NULL,
    workers           INTEGER NOT NULL,
    optimal_capacity  INTEGER NOT NULL,
    groups_json       TEXT    NOT NULL,
    algorithm_version TEXT    NOT NULL DEFAULT 'binary_search_v1',
    schema_version    INTEGER NOT NULL DEFAULT 1
);
"""


class PersistenceError(RuntimeError):
    """Raised when the SQLite layer cannot complete an operation."""


def _db_path() -> Path:
    """Return a platform-independent path for the LoadLens database.

    Uses the user's local application-data directory on each OS, falling
    back to the current working directory's `data/` subdirectory.
    No hard-coded drive letters or user-specific paths are embedded.
    """
    try:
        import os
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / ".local" / "share"
        db_dir = base / "loadlens"
    except Exception:
        db_dir = Path("data")
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "loadlens_scenarios.db"


class ScenarioRepository:
    """Data-access object for local scenario history.

    Instantiate once and reuse; the connection is opened lazily.
    If the database cannot be created or written, a PersistenceError is
    raised from each method — callers must handle this gracefully.

    Args:
        db_path: Optional explicit path to the SQLite database file.
                 Defaults to the platform-appropriate local data directory.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or _db_path()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Create tables if they do not already exist."""
        if self._initialized:
            return
        try:
            with self._connect() as conn:
                conn.executescript(_DDL)
            self._initialized = True
        except sqlite3.Error as exc:
            raise PersistenceError(
                f"Cannot initialize the LoadLens database at {self._db_path}: {exc}"
            ) from exc

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a database connection, yield it, then close it.

        Uses isolation_level=None for manual transaction control.
        """
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise PersistenceError(f"Database error: {exc}") from exc

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def save(self, record: ScenarioRecord) -> ScenarioRecord:
        """Insert a new scenario record and return it with the assigned ID.

        Args:
            record: ScenarioRecord to persist (scenario_id will be set by DB).

        Returns:
            The same record with scenario_id populated.

        Raises:
            PersistenceError: On database failure.
        """
        self._ensure_initialized()
        tasks_json = json.dumps(
            [{"name": t.name, "duration": t.duration} for t in record.tasks]
        )
        created_at = datetime.now(timezone.utc).isoformat()

        sql = """
            INSERT INTO scenarios
                (name, created_at, tasks_json, workers, optimal_capacity,
                 groups_json, algorithm_version, schema_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._connect() as conn:
                conn.execute("BEGIN")
                cursor = conn.execute(
                    sql,
                    (
                        record.name,
                        created_at,
                        tasks_json,
                        record.workers,
                        record.optimal_capacity,
                        record.groups_json,
                        record.algorithm_version,
                        record.schema_version,
                    ),
                )
                conn.execute("COMMIT")
                new_id = cursor.lastrowid
        except sqlite3.Error as exc:
            raise PersistenceError(f"Failed to save scenario: {exc}") from exc

        return ScenarioRecord(
            scenario_id=new_id,
            name=record.name,
            created_at=created_at,
            tasks=record.tasks,
            workers=record.workers,
            optimal_capacity=record.optimal_capacity,
            groups_json=record.groups_json,
            algorithm_version=record.algorithm_version,
            schema_version=record.schema_version,
        )

    def list_all(self) -> List[ScenarioRecord]:
        """Return all saved scenarios ordered by creation time (newest first).

        Raises:
            PersistenceError: On database failure.
        """
        self._ensure_initialized()
        sql = """
            SELECT scenario_id, name, created_at, tasks_json, workers,
                   optimal_capacity, groups_json, algorithm_version, schema_version
            FROM scenarios
            ORDER BY scenario_id DESC
        """
        try:
            with self._connect() as conn:
                rows = conn.execute(sql).fetchall()
        except sqlite3.Error as exc:
            raise PersistenceError(f"Failed to list scenarios: {exc}") from exc

        return [self._row_to_record(row) for row in rows]

    def get_by_id(self, scenario_id: int) -> Optional[ScenarioRecord]:
        """Return a single scenario by its primary key, or None if not found.

        Raises:
            PersistenceError: On database failure.
        """
        self._ensure_initialized()
        sql = """
            SELECT scenario_id, name, created_at, tasks_json, workers,
                   optimal_capacity, groups_json, algorithm_version, schema_version
            FROM scenarios
            WHERE scenario_id = ?
        """
        try:
            with self._connect() as conn:
                row = conn.execute(sql, (scenario_id,)).fetchone()
        except sqlite3.Error as exc:
            raise PersistenceError(f"Failed to retrieve scenario {scenario_id}: {exc}") from exc

        return self._row_to_record(row) if row else None

    def delete(self, scenario_id: int) -> bool:
        """Delete a scenario by its primary key.

        Args:
            scenario_id: Primary key to delete.

        Returns:
            True if a row was deleted, False if the ID was not found.

        Raises:
            PersistenceError: On database failure.
        """
        self._ensure_initialized()
        sql = "DELETE FROM scenarios WHERE scenario_id = ?"
        try:
            with self._connect() as conn:
                conn.execute("BEGIN")
                cursor = conn.execute(sql, (scenario_id,))
                conn.execute("COMMIT")
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            raise PersistenceError(f"Failed to delete scenario {scenario_id}: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ScenarioRecord:
        """Deserialize a database row into a ScenarioRecord."""
        try:
            tasks_data = json.loads(row["tasks_json"])
            tasks = [Task(name=t["name"], duration=t["duration"]) for t in tasks_data]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Malformed tasks_json for scenario %s: %s", row["scenario_id"], exc)
            tasks = []

        return ScenarioRecord(
            scenario_id=row["scenario_id"],
            name=row["name"],
            created_at=row["created_at"],
            tasks=tasks,
            workers=row["workers"],
            optimal_capacity=row["optimal_capacity"],
            groups_json=row["groups_json"],
            algorithm_version=row["algorithm_version"],
            schema_version=row["schema_version"],
        )
