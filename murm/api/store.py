"""
Project and run manager backed by SQLite.
Replaces MiroFish's in-memory TaskManager (state lost on restart) and
scattered JSON file writes with a single SQLite database per data directory.

Schema:
  projects:    project_id, title, created_at, seed_text, seed_filenames, ontology_json, status
  runs:        run_id, project_id, config_json, status, created_at, completed_at, report_md, error, ground_truth, brier_score
  events:      event_id, run_id, round, event_type, payload_json, ts
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from murm.config import settings


_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id   TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    created_at   REAL NOT NULL,
    seed_text    TEXT DEFAULT '',
    seed_files   TEXT DEFAULT '[]',
    ontology     TEXT DEFAULT '{}',
    status       TEXT DEFAULT 'created'
);

CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    project_id   TEXT NOT NULL,
    config       TEXT NOT NULL,
    status       TEXT DEFAULT 'pending',
    created_at   REAL NOT NULL,
    completed_at REAL,
    report_md    TEXT DEFAULT '',
    error        TEXT DEFAULT '',
    metrics      TEXT DEFAULT '{}',
    ground_truth TEXT,
    brier_score  REAL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_id     TEXT PRIMARY KEY,
    run_id       TEXT NOT NULL,
    round_num    INTEGER,
    event_type   TEXT NOT NULL,
    payload      TEXT NOT NULL,
    ts           REAL NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
"""


class ProjectStore:
    """Async SQLite-backed store for projects and simulation runs."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    # Projects

    async def create_project(self, title: str) -> str:
        pid = str(uuid.uuid4())
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO projects (project_id, title, created_at) VALUES (?, ?, ?)",
                (pid, title, time.time()),
            )
            await db.commit()
        return pid

    async def update_project(self, project_id: str, **fields: Any) -> None:
        allowed = {"title", "seed_text", "seed_files", "ontology", "status"}
        updates = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                   for k, v in fields.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                f"UPDATE projects SET {set_clause} WHERE project_id = ?",
                [*updates.values(), project_id],
            )
            await db.commit()

    async def get_project(self, project_id: str) -> dict | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM projects WHERE project_id = ?", (project_id,)
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["ontology"] = json.loads(d["ontology"] or "{}")
        d["seed_files"] = json.loads(d["seed_files"] or "[]")
        return d

    async def list_projects(self) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT project_id, title, created_at, status FROM projects ORDER BY created_at DESC"
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    # Runs

    async def create_run(self, run_id_or_project_id: str, project_id_or_config=None, config: dict | None = None) -> str:
        """Flexible overload:
        - create_run(project_id, config)            → generates a run_id
        - create_run(run_id, project_id, config)   → uses the supplied run_id
        """
        if config is None:
            # Called as create_run(project_id, config)
            project_id = run_id_or_project_id
            config = project_id_or_config
            rid = str(uuid.uuid4())
        else:
            # Called as create_run(run_id, project_id, config)
            rid = run_id_or_project_id
            project_id = project_id_or_config
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO runs (run_id, project_id, config, created_at) VALUES (?, ?, ?, ?)",
                (rid, project_id, json.dumps(config), time.time()),
            )
            await db.commit()
        return rid

    async def update_run(self, run_id: str, **fields: Any) -> None:
        allowed = {"status", "completed_at", "report_md", "error", "metrics", "ground_truth", "brier_score"}
        updates = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                   for k, v in fields.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                f"UPDATE runs SET {set_clause} WHERE run_id = ?",
                [*updates.values(), run_id],
            )
            await db.commit()

    async def get_run(self, run_id: str) -> dict | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["config"] = json.loads(d["config"] or "{}")
        d["metrics"] = json.loads(d["metrics"] or "{}")
        return d

    async def list_runs(self, project_id: str) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT run_id, status, created_at, completed_at FROM runs "
                "WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    # Events (SSE persistence)

    async def append_event(self, run_id: str, event_type: str, payload: dict,
                           round_num: int | None = None) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO events (event_id, run_id, round_num, event_type, payload, ts) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, round_num, event_type,
                 json.dumps(payload), time.time()),
            )
            await db.commit()

    # Deletion

    async def delete_project(self, project_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "DELETE FROM events WHERE run_id IN "
                "(SELECT run_id FROM runs WHERE project_id = ?)",
                (project_id,),
            )
            await db.execute("DELETE FROM runs WHERE project_id = ?", (project_id,))
            await db.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            await db.commit()

    async def delete_run(self, run_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM events WHERE run_id = ?", (run_id,))
            await db.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            await db.commit()

    async def get_events_since(self, run_id: str, since_ts: float = 0.0) -> list[dict]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM events WHERE run_id = ? AND ts > ? ORDER BY ts ASC",
                (run_id, since_ts),
            ) as cur:
                rows = await cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            result.append(d)
        return result

    async def get_events(self, run_id: str, since: float = 0.0) -> list[dict]:
        return await self.get_events_since(run_id, since_ts=since)

    async def add_event(self, run_id: str, event: dict) -> None:
        event_type = event.get("type", "unknown")
        payload    = event.get("payload", event)
        round_num  = event.get("round") or (payload.get("round") if isinstance(payload, dict) else None)
        await self.append_event(run_id, event_type, payload if isinstance(payload, dict) else {"data": payload}, round_num)

    async def resolve_run(self, run_id: str, ground_truth: str) -> dict:
        run = await self.get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        from murm.analysis.calibration import compute_brier_score
        dominant = run.get("metrics", {}).get("dominant_opinion", "neutral")
        
        # Binary Brier Mapping
        confidence = 0.8 # Default trust level
        match = (ground_truth.lower() == dominant.lower())
        brier = compute_brier_score(confidence, match)

        await self.update_run(run_id, ground_truth=ground_truth, brier_score=brier)
        return {"run_id": run_id, "brier_score": round(brier, 4), "match": match}
