import asyncio

from app.domain.models import GenerationJob
from app.ports.queue import JobQueue


class MemoryJobQueue(JobQueue):
    backend = "memory"

    def __init__(self) -> None:
        self._queue: asyncio.Queue[GenerationJob] = asyncio.Queue()

    async def enqueue(self, job: GenerationJob) -> None:
        await self._queue.put(job)

    async def fetch(self, timeout: float = 2.0) -> GenerationJob | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def healthcheck(self) -> None:
        return None
