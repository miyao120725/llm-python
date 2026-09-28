import json
from collections.abc import AsyncIterator
from dataclasses import asdict

import httpx

from app.core.exceptions import ProviderError
from app.domain.models import ChatMessage, LLMStreamPart
from app.providers.llm.base import LLMProvider

_DEEP_TIMEOUT = 300.0
_SEARCH_MODES = {"turbo", "max", "agent", "agent_max"}


class OpenAICompatLLMProvider(LLMProvider):
    name = "openai_compat"

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float = 180.0):
        super().__init__(model)
        self._base_url = base_url.rstrip("/")
        self._default_timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    def _resolve_model(self, model: str | None) -> str:
        if model and model.strip().lower() not in {"string", "none", "null"}:
            return model.strip()
        return self.model

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
        resolved_model = self._resolve_model(model)
        payload: dict = {
            "model": resolved_model,
            "messages": [asdict(item) for item in messages],
            "stream": True,
        }
        if not thinking:
            payload["temperature"] = temperature
        if "dashscope" in self._base_url:
            payload["enable_thinking"] = bool(thinking)
            strategy = resolve_search_strategy(resolved_model, search)
            if strategy:
                payload["enable_search"] = True
                payload["search_options"] = {
                    "search_strategy": strategy,
                    "forced_search": True,
                }
        timeout = _DEEP_TIMEOUT if thinking or search in _SEARCH_MODES else self._default_timeout
        try:
            async with self._client.stream(
                "POST",
                "/chat/completions",
                json=payload,
                timeout=timeout,
            ) as response:
                if response.status_code >= 400:
                    detail = await _read_error_body(response)
                    raise ProviderError(
                        f"LLM 请求失败: HTTP {response.status_code} {response.reason_phrase}。{detail}"
                    )
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                    else:
                        data = line.strip()
                    if not data or data == "[DONE]":
                        if data == "[DONE]":
                            break
                        continue
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    for part in _choice_parts(event):
                        yield part
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError(f"LLM 请求失败: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()


def resolve_search_strategy(model: str, search: str) -> str | None:
    if search not in _SEARCH_MODES:
        return None
    # qwen3.8 不支持 agent / agent_max，深度搜索降为 max
    if model.lower().startswith("qwen3.8"):
        if search == "turbo":
            return "turbo"
        return "max"
    return search


async def _read_error_body(response: httpx.Response) -> str:
    try:
        await response.aread()
    except httpx.HTTPError:
        return ""
    return (response.text or "")[:300]


def _choice_parts(event: dict) -> list[LLMStreamPart]:
    choices = event.get("choices") or [{}]
    choice = choices[0] if choices else {}
    delta = choice.get("delta") or {}
    message = choice.get("message") or {}
    parts: list[LLMStreamPart] = []
    reasoning = delta.get("reasoning_content") or message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning:
        parts.append(LLMStreamPart(kind="reasoning", text=reasoning))
    content = delta.get("content") or message.get("content")
    if isinstance(content, str) and content:
        parts.append(LLMStreamPart(kind="content", text=content))
    return parts
