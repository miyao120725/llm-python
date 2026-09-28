import asyncio
import time
import uuid
from threading import Lock

from app.core.exceptions import TaskNotFoundError, TaskTimeoutError
from app.domain.models import MediaObject, TaskRecord, TaskStatus, utc_now
from app.ports.tasks import TaskStore


class MemoryTaskStore(TaskStore):
    backend = "memory"

    def __init__(self) -> None:
        self._items: dict[str, TaskRecord] = {}
        self._lock = Lock()

    async def create(self, kind: str, prompt: str) -> TaskRecord:
        record = TaskRecord(
            task_id=uuid.uuid4().hex,
            kind=kind,
            status=TaskStatus.PENDING,
            prompt=prompt,
        )
        with self._lock:
            self._items[record.task_id] = record
        return record

    async def get(self, task_id: str) -> TaskRecord:
        with self._lock:
            record = self._items.get(task_id)
        if record is None:
            raise TaskNotFoundError(task_id)
        return record

    async def mark_running(self, task_id: str) -> TaskRecord:
        return self._update(task_id, status=TaskStatus.RUNNING)

    async def mark_succeeded(
        self,
        task_id: str,
        *,
        media: MediaObject,
        enhanced_prompt: str | None,
    ) -> TaskRecord:
        return self._update(
            task_id,
            status=TaskStatus.SUCCEEDED,
            media=media,
            enhanced_prompt=enhanced_prompt,
            error=None,
        )

    async def mark_failed(self, task_id: str, error: str) -> TaskRecord:
        return self._update(task_id, status=TaskStatus.FAILED, error=error)

    async def wait_until_done(self, task_id: str, timeout: float) -> TaskRecord:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = await self.get(task_id)
            if record.done:
                return record
            await asyncio.sleep(0.05)
        raise TaskTimeoutError(task_id)

    async def healthcheck(self) -> None:
        return None

    def _update(self, task_id: str, **changes) -> TaskRecord:
        with self._lock:
            record = self._items.get(task_id)
            if record is None:
                raise TaskNotFoundError(task_id)
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = utc_now()
            return record
