from dataclasses import dataclass, field
from typing import Any


@dataclass
class MediaBlob:
    data: bytes
    filename: str
    content_type: str
    url: str | None = None


@dataclass
class ImageResult:
    data: bytes | None = None
    url: str | None = None
    content_type: str = "image/png"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoResult:
    data: bytes | None = None
    url: str | None = None
    content_type: str = "video/mp4"
    provider_task_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
