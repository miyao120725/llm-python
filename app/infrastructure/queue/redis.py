import json

from app.core.exceptions import ConfigError
from app.domain.models import GenerationJob
from app.ports.queue import JobQueue


class RedisJobQueue(JobQueue):
    backend = "redis"

    def __init__(self, redis_url: str, name: str):
        try:
            from redis.asyncio import Redis
        except ImportError as exc:
            raise ConfigError("QUEUE_BACKEND=redis 需要安装 redis：pip install redis") from exc
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self.name = name

    async def enqueue(self, job: GenerationJob) -> None:
        await self._redis.lpush(self.name, json.dumps(job.to_dict(), ensure_ascii=False))

    async def fetch(self, timeout: float = 2.0) -> GenerationJob | None:
        item = await self._redis.brpop(self.name, timeout=max(1, int(timeout)))
        if not item:
            return None
        _, payload = item
        return GenerationJob.from_dict(json.loads(payload))

    async def healthcheck(self) -> None:
        await self._redis.ping()

    async def aclose(self) -> None:
        await self._redis.aclose()
