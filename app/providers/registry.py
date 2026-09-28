from dataclasses import dataclass

from app.config import Settings
from app.providers.image.base import ImageProvider
from app.providers.image.dashscope import DashScopeImageProvider
from app.providers.image.mock import MockImageProvider
from app.providers.image.openai_compat import OpenAICompatImageProvider
from app.providers.llm.base import LLMProvider
from app.providers.llm.mock import MockLLMProvider
from app.providers.llm.openai_compat import OpenAICompatLLMProvider
from app.providers.video.base import VideoProvider
from app.providers.video.dashscope import DashScopeVideoProvider
from app.providers.video.http import HttpVideoProvider
from app.providers.video.mock import MockVideoProvider


@dataclass
class Providers:
    llm: LLMProvider
    image: ImageProvider
    video: VideoProvider

    async def aclose(self) -> None:
        await self.llm.aclose()
        await self.image.aclose()
        await self.video.aclose()


def build_providers(settings: Settings) -> Providers:
    llm: LLMProvider
    if settings.use_mock_llm():
        llm = MockLLMProvider(settings.llm_model)
    elif settings.llm_provider == "openai_compat":
        llm = OpenAICompatLLMProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    else:
        raise ValueError(f"不支持的 LLM provider: {settings.llm_provider}")

    image: ImageProvider
    if settings.use_mock_image():
        image = MockImageProvider(settings.image_model)
    elif settings.image_provider == "openai_compat":
        image = OpenAICompatImageProvider(
            base_url=settings.image_base_url,
            api_key=settings.image_api_key,
            model=settings.image_model,
            default_size=settings.image_size,
        )
    elif settings.image_provider == "dashscope":
        image = DashScopeImageProvider(
            base_url=settings.image_base_url,
            api_key=settings.resolved_image_api_key,
            model=settings.image_model,
            default_size=settings.image_size,
        )
    else:
        raise ValueError(f"不支持的 Image provider: {settings.image_provider}")

    video: VideoProvider
    if settings.use_mock_video():
        video = MockVideoProvider(settings.video_model)
    elif settings.video_provider == "http":
        video = HttpVideoProvider(
            base_url=settings.video_base_url,
            api_key=settings.video_api_key,
            model=settings.video_model,
            image_to_video_path=settings.video_image_to_video_path,
            video_to_video_path=settings.video_video_to_video_path,
            task_path=settings.video_task_path,
            poll_interval=settings.video_poll_interval_seconds,
            poll_timeout=settings.video_poll_timeout_seconds,
        )
    elif settings.video_provider == "dashscope":
        video = DashScopeVideoProvider(
            base_url=settings.video_base_url,
            api_key=settings.resolved_video_api_key,
            model=settings.video_model,
            poll_interval=settings.video_poll_interval_seconds,
            poll_timeout=settings.video_poll_timeout_seconds,
        )
    else:
        raise ValueError(f"不支持的 Video provider: {settings.video_provider}")

    return Providers(llm=llm, image=image, video=video)
