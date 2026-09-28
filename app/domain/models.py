from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMStreamPart:
    kind: str
    text: str


@dataclass
class MediaObject:
    file_id: str
    filename: str
    content_type: str
    url: str
    size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> MediaObject | None:
        if not data:
            return None
        return cls(**data)


@dataclass
class TaskRecord:
    task_id: str
    kind: str
    status: TaskStatus
    prompt: str
    enhanced_prompt: str | None = None
    media: MediaObject | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def done(self) -> bool:
        return self.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED}


@dataclass
class ConversationMessage:
    role: str
    content: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class Conversation:
    conversation_id: str
    created_at: datetime = field(default_factory=utc_now)
    messages: list[ConversationMessage] = field(default_factory=list)


@dataclass
class ConversationSummary:
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    title: str
    last_role: str
    last_content: str
    message_count: int


@dataclass
class GenerationJob:
    task_id: str
    kind: str
    prompt: str
    enhance_prompt: bool = False
    size: str | None = None
    duration_seconds: float = 5
    resolution: str | None = None
    ratio: str | None = None
    strength: float = 0.6
    input_file_id: str | None = None
    input_filename: str | None = None
    input_content_type: str | None = None
    input_image_id: str | None = None
    input_image_filename: str | None = None
    input_image_content_type: str | None = None
    input_video_id: str | None = None
    input_video_filename: str | None = None
    input_video_content_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationJob:
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in allowed})
