from abc import ABC, abstractmethod

from app.domain.models import MediaObject, TaskRecord


class TaskStore(ABC):
    backend: str = "tasks"

    @abstractmethod
    async def create(self, kind: str, prompt: str) -> TaskRecord:
        raise NotImplementedError

    @abstractmethod
    async def get(self, task_id: str) -> TaskRecord:
        raise NotImplementedError

    @abstractmethod
    async def mark_running(self, task_id: str) -> TaskRecord:
        raise NotImplementedError

    @abstractmethod
    async def mark_succeeded(
        self,
        task_id: str,
        *,
        media: MediaObject,
        enhanced_prompt: str | None,
    ) -> TaskRecord:
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(self, task_id: str, error: str) -> TaskRecord:
        raise NotImplementedError

    @abstractmethod
    async def wait_until_done(self, task_id: str, timeout: float) -> TaskRecord:
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> None:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None
