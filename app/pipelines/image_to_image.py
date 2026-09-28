from app.domain.models import MediaObject
from app.pipelines.media import persist_image
from app.ports.storage import ObjectStorage
from app.providers.image.base import ImageProvider
from app.providers.llm.base import LLMProvider
from app.providers.types import MediaBlob


class ImageToImagePipeline:
    def __init__(self, llm: LLMProvider, image: ImageProvider, storage: ObjectStorage):
        self.llm = llm
        self.image = image
        self.storage = storage

    async def run(
        self,
        prompt: str,
        image: MediaBlob,
        *,
        enhance_prompt: bool = False,
        size: str | None = None,
        strength: float = 0.6,
    ) -> tuple[str, MediaObject]:
        final_prompt = prompt
        if enhance_prompt:
            final_prompt = await self.llm.enhance_prompt(prompt, "image")
        result = await self.image.edit(
            final_prompt,
            image,
            size=size,
            strength=strength,
        )
        media = await persist_image(self.storage, result)
        return final_prompt, media
