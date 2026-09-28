from abc import ABC, abstractmethod
from pathlib import Path

from app.domain.models import MediaObject


class ObjectStorage(ABC):
    backend: str = "storage"

    @abstractmethod
    async def save_bytes(self, data: bytes, *, suffix: str, content_type: str) -> MediaObject:
        raise NotImplementedError

    @abstractmethod
    async def get_bytes(self, file_id: str) -> bytes:
        raise NotImplementedError

    async def local_path(self, file_id: str) -> Path | None:
        return None

    async def presigned_url(self, file_id: str) -> str | None:
        return None

    @abstractmethod
    async def healthcheck(self) -> None:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None
