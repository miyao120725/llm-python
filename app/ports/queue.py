from abc import ABC, abstractmethod

from app.domain.models import GenerationJob


class JobQueue(ABC):
    backend: str = "queue"

    @abstractmethod
    async def enqueue(self, job: GenerationJob) -> None:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, timeout: float = 2.0) -> GenerationJob | None:
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> None:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None
