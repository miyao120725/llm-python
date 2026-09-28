from __future__ import annotations

import json
from collections.abc import AsyncIterator

from app.core.exceptions import AppError, InvalidConversationTurnError
from app.domain.models import ChatMessage, Conversation, ConversationSummary
from app.ports.conversations import ConversationStore
from app.providers.llm.base import LLMProvider
from app.schemas.llm import ChatMessage as ChatMessageSchema
from app.schemas.llm import ChatResponse, SearchMode

_TITLE_MAX = 40
_PREVIEW_MAX = 80


class ConversationService:
    def __init__(
        self,
        *,
        store: ConversationStore,
        llm: LLMProvider,
        history_limit: int,
    ):
        self.store = store
        self.llm = llm
        self.history_limit = max(1, history_limit)

    async def create(self) -> Conversation:
        return await self.store.create()

    async def get(self, conversation_id: str) -> Conversation:
        return await self.store.get(conversation_id)

    async def list_recent(self, limit: int) -> list[ConversationSummary]:
        items = await self.store.list_recent(limit)
        return [
            ConversationSummary(
                conversation_id=item.conversation_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                title=_clip(item.title, _TITLE_MAX),
                last_role=item.last_role,
                last_content=_clip(item.last_content, _PREVIEW_MAX),
                message_count=item.message_count,
            )
            for item in items
        ]

    async def complete(
        self,
        *,
        messages: list[ChatMessageSchema],
        conversation_id: str | None,
        temperature: float,
        model: str | None,
        thinking: bool = False,
        search: SearchMode = "off",
    ) -> ChatResponse:
        outgoing, conversation_id = await self._prepare(messages, conversation_id)
        outgoing = _with_search_hint(outgoing, search)
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        async for part in self.llm.chat_stream(
            outgoing,
            temperature=temperature,
            model=model,
            thinking=thinking,
            search=search,
        ):
            if part.kind == "reasoning":
                reasoning_parts.append(part.text)
            elif part.kind == "content":
                content_parts.append(part.text)
        content = "".join(content_parts)
        if conversation_id:
            await self.store.add_message(conversation_id, "assistant", content)
        return ChatResponse(
            content=content,
            model=model or self.llm.model,
            mocked=self.llm.mocked,
            conversation_id=conversation_id,
            reasoning="".join(reasoning_parts) or None,
            thinking=thinking,
            search=search,
        )

    async def stream(
        self,
        *,
        messages: list[ChatMessageSchema],
        conversation_id: str | None,
        temperature: float,
        model: str | None,
        thinking: bool = False,
        search: SearchMode = "off",
    ) -> AsyncIterator[str]:
        outgoing, conversation_id = await self._prepare(messages, conversation_id)
        outgoing = _with_search_hint(outgoing, search)
        resolved_model = model or self.llm.model
        chunks: list[str] = []
        persisted = False
        try:
            async for part in self.llm.chat_stream(
                outgoing,
                temperature=temperature,
                model=model,
                thinking=thinking,
                search=search,
            ):
                if part.kind == "reasoning":
                    yield _sse({"type": "reasoning", "content": part.text})
                    continue
                if part.kind == "content" and part.text:
                    chunks.append(part.text)
                    yield _sse({"type": "delta", "content": part.text})
            await self._persist_assistant(conversation_id, chunks)
            persisted = True
            yield _sse(
                {
                    "type": "done",
                    "conversation_id": conversation_id,
                    "model": resolved_model,
                    "thinking": thinking,
                    "search": search,
                }
            )
            yield "data: [DONE]\n\n"
        except AppError as exc:
            yield _sse({"type": "error", "message": exc.message, "code": exc.code})
        finally:
            if not persisted:
                await self._persist_assistant(conversation_id, chunks)

    async def _prepare(
        self,
        messages: list[ChatMessageSchema],
        conversation_id: str | None,
    ) -> tuple[list[ChatMessage], str | None]:
        if not conversation_id:
            return (
                [ChatMessage(role=item.role, content=item.content) for item in messages],
                None,
            )
        if len(messages) != 1 or messages[0].role != "user":
            raise InvalidConversationTurnError()
        conversation = await self.store.get(conversation_id)
        await self.store.add_message(conversation_id, "user", messages[0].content)
        history = [
            ChatMessage(role=item.role, content=item.content) for item in conversation.messages
        ]
        history.append(ChatMessage(role="user", content=messages[0].content))
        return history[-self.history_limit :], conversation_id

    async def _persist_assistant(self, conversation_id: str | None, chunks: list[str]) -> None:
        text = "".join(chunks)
        if conversation_id and text:
            await self.store.add_message(conversation_id, "assistant", text)


def _with_search_hint(messages: list[ChatMessage], search: SearchMode) -> list[ChatMessage]:
    if search == "off":
        return messages
    hint = ChatMessage(
        role="system",
        content="已开启联网搜索。请根据检索结果回答时效性问题，不要说无法联网或没有实时数据。",
    )
    return [hint, *messages]


def _clip(text: str, max_len: int) -> str:
    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped
    return stripped[:max_len].rstrip() + "…"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
