from app.domain.models import MediaObject
from app.pipelines.media import persist_video
from app.ports.storage import ObjectStorage
from app.providers.llm.base import LLMProvider
from app.providers.types import MediaBlob
from app.providers.video.base import VideoProvider


class VideoGeneratePipeline:
    def __init__(self, llm: LLMProvider, video: VideoProvider, storage: ObjectStorage):
        self.llm = llm
        self.video = video
        self.storage = storage

    async def run(
        self,
        prompt: str,
        *,
        image: MediaBlob | None = None,
        video: MediaBlob | None = None,
        enhance_prompt: bool = False,
        duration_seconds: float = 5,
        resolution: str = "720P",
        ratio: str = "adaptive",
    ) -> tuple[str, MediaObject]:
        final_prompt = prompt
        if enhance_prompt and prompt.strip():
            final_prompt = await self.llm.enhance_prompt(prompt, "video")
        result = await self.video.synthesize(
            prompt=final_prompt,
            image=image,
            video=video,
            duration_seconds=duration_seconds,
            resolution=resolution,
            ratio=ratio,
        )
        media = await persist_video(self.storage, result)
        return final_prompt, media
