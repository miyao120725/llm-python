from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.domain.models import ChatMessage, LLMStreamPart


class LLMProvider(ABC):
    name: str = "llm"
    mocked: bool = False

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        model: str | None = None,
        thinking: bool = False,
        search: str = "off",
    ) -> str:
        raise NotImplementedError

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        model: str | None = None,
        thinking: bool = False,
        search: str = "off",
    ) -> AsyncIterator[LLMStreamPart]:
        content = await self.chat(
            messages,
            temperature=temperature,
            model=model,
            thinking=thinking,
            search=search,
        )
        if content:
            yield LLMStreamPart(kind="content", text=content)

    async def enhance_prompt(self, prompt: str, mode: str) -> str:
        mode_hint = {
            "image": "你是专业的文生图提示词工程师。把用户短句扩写成适合图像模型的详细英文或中英混合提示词，包含主体、风格、构图、光影、镜头。只输出提示词本身。",
            "video": "你是专业的视频生成提示词工程师。根据用户描述写出主体、动作、运镜、节奏、氛围，适合视频模型。只输出提示词本身。",
            "image_to_video": "你是专业的图生视频提示词工程师。根据用户描述写出运镜、动作、节奏、氛围，适合视频模型。只输出提示词本身。",
            "video_to_video": "你是专业的视频再生成提示词工程师。描述如何在保留原视频主体的前提下改变风格、动作或镜头。只输出提示词本身。",
        }
        system = mode_hint.get(mode, mode_hint["image"])
        return await self.chat(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=0.8,
        )

    async def aclose(self) -> None:
        return None
