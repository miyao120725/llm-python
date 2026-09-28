import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite

from app.core.exceptions import TaskNotFoundError, TaskTimeoutError
from app.domain.models import MediaObject, TaskRecord, TaskStatus, utc_now
from app.ports.tasks import TaskStore

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    media_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SqliteTaskStore(TaskStore):
    backend = "sqlite"

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ready = False

    async def init(self) -> None:
        if self._ready:
            return
        async with aiosqlite.connect(self.path) as db:
            await db.execute(_CREATE_SQL)
            await db.commit()
        self._ready = True

    async def create(self, kind: str, prompt: str) -> TaskRecord:
        await self.init()
        record = TaskRecord(
            task_id=uuid.uuid4().hex,
            kind=kind,
            status=TaskStatus.PENDING,
            prompt=prompt,
        )
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO tasks (task_id, kind, status, prompt, enhanced_prompt, media_json, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.task_id,
                    record.kind,
                    record.status.value,
                    record.prompt,
                    record.enhanced_prompt,
                    None,
                    record.error,
                    _iso(record.created_at),
                    _iso(record.updated_at),
                ),
            )
            await db.commit()
        return record

    async def get(self, task_id: str) -> TaskRecord:
        await self.init()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = await cursor.fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        return self._row_to_record(row)

    async def mark_running(self, task_id: str) -> TaskRecord:
        return await self._update(task_id, status=TaskStatus.RUNNING)

    async def mark_succeeded(
        self,
        task_id: str,
        *,
        media: MediaObject,
        enhanced_prompt: str | None,
    ) -> TaskRecord:
        return await self._update(
            task_id,
            status=TaskStatus.SUCCEEDED,
            media=media,
            enhanced_prompt=enhanced_prompt,
            error=None,
        )

    async def mark_failed(self, task_id: str, error: str) -> TaskRecord:
        return await self._update(task_id, status=TaskStatus.FAILED, error=error)

    async def wait_until_done(self, task_id: str, timeout: float) -> TaskRecord:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = await self.get(task_id)
            if record.done:
                return record
            await asyncio.sleep(0.05)
        raise TaskTimeoutError(task_id)

    async def healthcheck(self) -> None:
        await self.init()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("SELECT 1")

    async def _update(self, task_id: str, **changes) -> TaskRecord:
        record = await self.get(task_id)
        for key, value in changes.items():
            setattr(record, key, value)
        record.updated_at = utc_now()
        media_json = json.dumps(record.media.to_dict()) if record.media else None
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET status = ?, enhanced_prompt = ?, media_json = ?, error = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    record.status.value,
                    record.enhanced_prompt,
                    media_json,
                    record.error,
                    _iso(record.updated_at),
                    task_id,
                ),
            )
            await db.commit()
        return record

    @staticmethod
    def _row_to_record(row: aiosqlite.Row) -> TaskRecord:
        media = None
        if row["media_json"]:
            media = MediaObject.from_dict(json.loads(row["media_json"]))
        return TaskRecord(
            task_id=row["task_id"],
            kind=row["kind"],
            status=TaskStatus(row["status"]),
            prompt=row["prompt"],
            enhanced_prompt=row["enhanced_prompt"],
            media=media,
            error=row["error"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )
