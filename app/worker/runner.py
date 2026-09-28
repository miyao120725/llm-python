import logging

from app.domain.models import GenerationJob
from app.pipelines.image_to_image import ImageToImagePipeline
from app.pipelines.text_to_image import TextToImagePipeline
from app.pipelines.video_generate import VideoGeneratePipeline
from app.ports.queue import JobQueue
from app.ports.storage import ObjectStorage
from app.ports.tasks import TaskStore
from app.providers.types import MediaBlob

logger = logging.getLogger(__name__)

_VIDEO_KINDS = {
    "text_to_video",
    "image_to_video",
    "video_to_video",
    "image_and_video_to_video",
}


class Worker:
    def __init__(
        self,
        *,
        queue: JobQueue,
        tasks: TaskStore,
        storage: ObjectStorage,
        text_to_image: TextToImagePipeline,
        image_to_image: ImageToImagePipeline,
        video_generate: VideoGeneratePipeline,
    ):
        self.queue = queue
        self.tasks = tasks
        self.storage = storage
        self._text_to_image = text_to_image
        self._image_to_image = image_to_image
        self._video_generate = video_generate
        self._running = False

    async def run_forever(self) -> None:
        self._running = True
        logger.info("worker started backend=%s", self.queue.backend)
        while self._running:
            job = await self.queue.fetch(timeout=2.0)
            if job is None:
                continue
            await self.handle(job)

    def stop(self) -> None:
        self._running = False

    async def handle(self, job: GenerationJob) -> None:
        await self.tasks.mark_running(job.task_id)
        try:
            enhanced_prompt, media = await self._run(job)
            await self.tasks.mark_succeeded(
                job.task_id,
                media=media,
                enhanced_prompt=enhanced_prompt,
            )
        except Exception as exc:
            logger.exception("worker job failed task_id=%s", job.task_id)
            await self.tasks.mark_failed(job.task_id, str(exc))

    async def _run(self, job: GenerationJob):
        if job.kind == "text_to_image":
            return await self._text_to_image.run(
                job.prompt,
                enhance_prompt=job.enhance_prompt,
                size=job.size,
            )
        if job.kind == "image_to_image":
            blob = await self._load_blob(
                job.input_file_id,
                job.input_filename,
                job.input_content_type,
            )
            return await self._image_to_image.run(
                job.prompt,
                blob,
                enhance_prompt=job.enhance_prompt,
                size=job.size,
                strength=job.strength,
            )
        if job.kind in _VIDEO_KINDS:
            image = await self._optional_blob(
                job.input_image_id,
                job.input_image_filename,
                job.input_image_content_type,
            )
            video = await self._optional_blob(
                job.input_video_id,
                job.input_video_filename,
                job.input_video_content_type,
            )
            return await self._video_generate.run(
                job.prompt,
                image=image,
                video=video,
                enhance_prompt=job.enhance_prompt,
                duration_seconds=job.duration_seconds,
                resolution=job.resolution or "720P",
                ratio=job.ratio or "adaptive",
            )
        raise ValueError(f"未知任务类型: {job.kind}")

    async def _optional_blob(
        self,
        file_id: str | None,
        filename: str | None,
        content_type: str | None,
    ) -> MediaBlob | None:
        if not file_id:
            return None
        return await self._load_blob(file_id, filename, content_type)

    async def _load_blob(
        self,
        file_id: str | None,
        filename: str | None,
        content_type: str | None,
    ) -> MediaBlob:
        if not file_id:
            raise ValueError("任务缺少输入文件")
        data = await self.storage.get_bytes(file_id)
        return MediaBlob(
            data=data,
            filename=filename or file_id,
            content_type=content_type or "application/octet-stream",
        )
