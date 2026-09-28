from app.config import Settings
from app.core.exceptions import ConfigError
from app.infrastructure.conversations.sqlite import SqliteConversationStore
from app.infrastructure.queue.memory import MemoryJobQueue
from app.infrastructure.queue.redis import RedisJobQueue
from app.infrastructure.storage.local import LocalObjectStorage
from app.infrastructure.storage.s3 import S3ObjectStorage
from app.infrastructure.tasks.memory import MemoryTaskStore
from app.infrastructure.tasks.sqlite import SqliteTaskStore
from app.ports.conversations import ConversationStore
from app.ports.queue import JobQueue
from app.ports.storage import ObjectStorage
from app.ports.tasks import TaskStore


def build_storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "local":
        return LocalObjectStorage(settings.storage_dir)
    if settings.storage_backend == "s3":
        return S3ObjectStorage(
            bucket=settings.s3_bucket,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            public_base_url=settings.s3_public_base_url,
        )
    raise ConfigError(f"不支持的 STORAGE_BACKEND: {settings.storage_backend}")


def build_task_store(settings: Settings) -> TaskStore:
    if settings.task_backend == "memory":
        return MemoryTaskStore()
    if settings.task_backend == "sqlite":
        return SqliteTaskStore(settings.sqlite_path)
    raise ConfigError(f"不支持的 TASK_BACKEND: {settings.task_backend}")


def build_conversation_store(settings: Settings) -> ConversationStore:
    return SqliteConversationStore(settings.sqlite_path)


def build_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "memory":
        return MemoryJobQueue()
    if settings.queue_backend == "redis":
        return RedisJobQueue(settings.redis_url, settings.queue_name)
    raise ConfigError(f"不支持的 QUEUE_BACKEND: {settings.queue_backend}")
