from abc import ABC, abstractmethod

from app.providers.types import MediaBlob, VideoResult


class VideoProvider(ABC):
    name: str = "video"
    mocked: bool = False

    def __init__(self, model: str = ""):
        self.model = model

    @abstractmethod
    async def synthesize(
        self,
        *,
        prompt: str,
        image: MediaBlob | None = None,
        video: MediaBlob | None = None,
        duration_seconds: float = 5,
        resolution: str = "720P",
        ratio: str = "adaptive",
    ) -> VideoResult:
        raise NotImplementedError

    async def image_to_video(
        self,
        *,
        prompt: str,
        image: MediaBlob,
        duration_seconds: float = 4,
    ) -> VideoResult:
        return await self.synthesize(
            prompt=prompt,
            image=image,
            duration_seconds=duration_seconds,
        )

    async def video_to_video(
        self,
        *,
        prompt: str,
        video: MediaBlob,
        strength: float = 0.6,
    ) -> VideoResult:
        return await self.synthesize(prompt=prompt, video=video)

    async def aclose(self) -> None:
        return None
