from collections.abc import AsyncIterator

from app.domain.models import ChatMessage, LLMStreamPart
from app.providers.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"
    mocked = True

    def __init__(self, model: str):
        super().__init__(model)
        self.last_messages: list[ChatMessage] = []
        self.last_thinking = False
        self.last_search = "off"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        model: str | None = None,
        thinking: bool = False,
        search: str = "off",
    ) -> str:
        chunks: list[str] = []
        async for part in self.chat_stream(
            messages,
            temperature=temperature,
            model=model,
            thinking=thinking,
            search=search,
        ):
            if part.kind == "content":
                chunks.append(part.text)
        return "".join(chunks)

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        model: str | None = None,
        thinking: bool = False,
        search: str = "off",
    ) -> AsyncIterator[LLMStreamPart]:
        self.last_messages = list(messages)
        self.last_thinking = thinking
        self.last_search = search
        last_user = next((item.content for item in reversed(messages) if item.role == "user"), "")
        if thinking:
            yield LLMStreamPart(kind="reasoning", text="先分析问题。")
            yield LLMStreamPart(kind="reasoning", text="再给出结论。")
        prefix = f"[mock-search:{search}] " if search != "off" else ""
        text = (
            f"{prefix}[mock-llm] cinematic lighting, highly detailed, {last_user.strip()}, "
            "8k, masterpiece"
        )
        for index in range(0, len(text), 12):
            yield LLMStreamPart(kind="content", text=text[index : index + 12])
