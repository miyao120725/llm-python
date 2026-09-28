from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SearchMode = Literal["off", "turbo", "max", "agent", "agent_max"]

_MODEL_PLACEHOLDERS = {"", "string", "none", "null"}
_SEARCH_OFF = {"", "string", "none", "null", "off", "false", "no", "0"}
_SEARCH_DEEP = {
    "true",
    "on",
    "1",
    "deep",
    "search",
    "agent_max",
    "深度搜索",
    "联网搜索",
    "联网",
    "搜索",
}
_SEARCH_ALIASES = (
    "deep_search",
    "deepSearch",
    "enable_search",
    "enableSearch",
    "web_search",
    "webSearch",
    "search_enabled",
)
_THINKING_ALIASES = ("deep_thinking", "deepThinking", "enable_thinking", "enableThinking")
_THINKING_ON = {"true", "on", "1", "深度推理", "思考"}


def coerce_search(value) -> str:
    if value is True or value == 1:
        return "agent_max"
    if value is False or value == 0 or value is None:
        return "off"
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if lowered in _SEARCH_OFF:
            return "off"
        if lowered in _SEARCH_DEEP or stripped in _SEARCH_DEEP:
            return "agent_max"
        if lowered in {"turbo", "max", "agent"}:
            return lowered
    return "off"


def resolve_optional_model(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped.lower() in _MODEL_PLACEHOLDERS:
        return None
    return stripped


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = Field(default=0.7, ge=0, le=2)
    model: str | None = Field(default=None, description="不填则使用 .env 的 LLM_MODEL；文档页不要填 string")
    conversation_id: str | None = Field(default=None, description="有值则走会话记忆，本轮只发一条 user")
    stream: bool = Field(default=False, description="true 时返回 SSE")
    thinking: bool = Field(default=False, description="深度推理，SSE 会先推 reasoning")
    search: SearchMode = Field(
        default="off",
        description="off / turbo / max / agent / agent_max；true 视为 agent_max。qwen3.8 会降为 max",
    )

    @field_validator("model", "conversation_id", mode="before")
    @classmethod
    def drop_placeholder(cls, value):
        if isinstance(value, str):
            return resolve_optional_model(value)
        return value

    @model_validator(mode="before")
    @classmethod
    def accept_client_aliases(cls, data):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        search = payload.get("search")
        if search in (None, "", "off"):
            for key in _SEARCH_ALIASES:
                if key in payload:
                    payload["search"] = payload[key]
                    break
        thinking = payload.get("thinking")
        if thinking in (None, False, ""):
            for key in _THINKING_ALIASES:
                if key in payload:
                    payload["thinking"] = payload[key]
                    break
        return payload

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value):
        return coerce_search(value)

    @field_validator("thinking", mode="before")
    @classmethod
    def normalize_thinking(cls, value):
        if isinstance(value, str) and value.strip() in _THINKING_ON:
            return True
        return value


class ChatResponse(BaseModel):
    content: str
    model: str
    mocked: bool = False
    conversation_id: str | None = None
    reasoning: str | None = None
    thinking: bool = False
    search: SearchMode = "off"


class ConversationCreateResponse(BaseModel):
    conversation_id: str
    created_at: datetime


class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[HistoryMessage]


class ConversationListItem(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_role: str
    last_content: str
    message_count: int


class ConversationListResponse(BaseModel):
    items: list[ConversationListItem]


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(min_length=1)
    mode: str = Field(default="image", pattern="^(image|video|image_to_video|video_to_video)$")


class EnhancePromptResponse(BaseModel):
    original: str
    enhanced: str
    mocked: bool = False
