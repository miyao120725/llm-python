from abc import ABC, abstractmethod

from app.providers.types import ImageResult, MediaBlob


class ImageProvider(ABC):
    name: str = "image"
    mocked: bool = False

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def generate(self, prompt: str, *, size: str | None = None) -> ImageResult:
        raise NotImplementedError

    async def edit(
        self,
        prompt: str,
        image: MediaBlob,
        *,
        size: str | None = None,
        strength: float = 0.6,
    ) -> ImageResult:
        return await self.generate(prompt, size=size)

    async def aclose(self) -> None:
        return None
