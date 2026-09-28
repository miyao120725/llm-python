import asyncio
import uuid
from pathlib import Path

from app.core.exceptions import MediaNotFoundError
from app.core.files import validate_file_id
from app.domain.models import MediaObject
from app.ports.storage import ObjectStorage


class LocalObjectStorage(ObjectStorage):
    backend = "local"

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_bytes(self, data: bytes, *, suffix: str, content_type: str) -> MediaObject:
        file_id = f"{uuid.uuid4().hex}{suffix}"
        path = self.root / file_id
        await asyncio.to_thread(path.write_bytes, data)
        return MediaObject(
            file_id=file_id,
            filename=file_id,
            content_type=content_type,
            url=f"/v1/media/{file_id}",
            size=len(data),
        )

    async def get_bytes(self, file_id: str) -> bytes:
        path = await self.local_path(file_id)
        if path is None:
            raise MediaNotFoundError(file_id)
        return await asyncio.to_thread(path.read_bytes)

    async def local_path(self, file_id: str) -> Path | None:
        validate_file_id(file_id)
        path = (self.root / file_id).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise MediaNotFoundError(file_id)
        return path

    async def healthcheck(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        probe = self.root / ".healthcheck"
        await asyncio.to_thread(probe.write_text, "ok", encoding="utf-8")
        await asyncio.to_thread(probe.unlink, True)
