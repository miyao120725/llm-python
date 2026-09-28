from app.domain.models import GenerationJob, MediaObject, TaskRecord
from app.ports.queue import JobQueue
from app.ports.storage import ObjectStorage
from app.ports.tasks import TaskStore
from app.providers.types import MediaBlob
from app.schemas.generate import GenerationResult
from app.schemas.task import TaskResponse


class GenerationService:
    def __init__(
        self,
        *,
        tasks: TaskStore,
        queue: JobQueue,
        storage: ObjectStorage,
        wait_timeout: float,
        video_wait_timeout: float | None = None,
    ):
        self.tasks = tasks
        self.queue = queue
        self.storage = storage
        self.wait_timeout = wait_timeout
        self.video_wait_timeout = video_wait_timeout or wait_timeout

    async def text_to_image(
        self,
        prompt: str,
        *,
        enhance_prompt: bool = False,
        size: str | None = None,
        async_mode: bool = False,
    ) -> TaskRecord:
        task = await self.tasks.create("text_to_image", prompt)
        await self.queue.enqueue(
            GenerationJob(
                task_id=task.task_id,
                kind="text_to_image",
                prompt=prompt,
                enhance_prompt=enhance_prompt,
                size=size,
            )
        )
        return await self._maybe_wait(task, async_mode)

    async def image_to_image(
        self,
        prompt: str,
        image: MediaBlob,
        *,
        enhance_prompt: bool = False,
        size: str | None = None,
        strength: float = 0.6,
        async_mode: bool = False,
    ) -> TaskRecord:
        task = await self.tasks.create("image_to_image", prompt)
        media = await self._store_input(image, fallback_suffix=".png")
        await self.queue.enqueue(
            GenerationJob(
                task_id=task.task_id,
                kind="image_to_image",
                prompt=prompt,
                enhance_prompt=enhance_prompt,
                size=size,
                strength=strength,
                input_file_id=media.file_id,
                input_filename=image.filename,
                input_content_type=image.content_type,
            )
        )
        return await self._maybe_wait(task, async_mode)

    async def generate_video(
        self,
        prompt: str,
        *,
        image: MediaBlob | None = None,
        video: MediaBlob | None = None,
        enhance_prompt: bool = False,
        duration_seconds: float = 5,
        resolution: str = "720P",
        ratio: str = "adaptive",
        async_mode: bool = True,
    ) -> TaskRecord:
        kind = _video_kind(image, video)
        task = await self.tasks.create(kind, prompt)
        image_media = await self._store_input(image, fallback_suffix=".png") if image else None
        video_media = await self._store_input(video, fallback_suffix=".mp4") if video else None
        await self.queue.enqueue(
            GenerationJob(
                task_id=task.task_id,
                kind=kind,
                prompt=prompt,
                enhance_prompt=enhance_prompt,
                duration_seconds=duration_seconds,
                resolution=resolution,
                ratio=ratio,
                input_image_id=image_media.file_id if image_media else None,
                input_image_filename=image.filename if image else None,
                input_image_content_type=image.content_type if image else None,
                input_video_id=video_media.file_id if video_media else None,
                input_video_filename=video.filename if video else None,
                input_video_content_type=video.content_type if video else None,
            )
        )
        return await self._maybe_wait(
            task,
            async_mode,
            timeout=self.video_wait_timeout,
        )

    async def get_task(self, task_id: str) -> TaskRecord:
        return await self.tasks.get(task_id)

    async def _store_input(self, blob: MediaBlob, *, fallback_suffix: str) -> MediaObject:
        suffix = ""
        if "." in blob.filename:
            suffix = "." + blob.filename.rsplit(".", 1)[-1].lower()
        return await self.storage.save_bytes(
            blob.data,
            suffix=suffix or fallback_suffix,
            content_type=blob.content_type,
        )

    async def _maybe_wait(
        self,
        task: TaskRecord,
        async_mode: bool,
        *,
        timeout: float | None = None,
    ) -> TaskRecord:
        if async_mode:
            return task
        return await self.tasks.wait_until_done(task.task_id, timeout or self.wait_timeout)


def to_generation_result(task: TaskResponse) -> GenerationResult:
    return GenerationResult(
        task_id=task.task_id,
        kind=task.kind,
        status=task.status,
        prompt=task.prompt,
        enhanced_prompt=task.enhanced_prompt,
        media=task.media,
        error=task.error,
    )


def _video_kind(image: MediaBlob | None, video: MediaBlob | None) -> str:
    if image and video:
        return "image_and_video_to_video"
    if image:
        return "image_to_video"
    if video:
        return "video_to_video"
    return "text_to_video"
