from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_container
from app.api.mappers import task_to_response
from app.container import AppContainer
from app.core.exceptions import UploadTooLargeError
from app.core.files import IMAGE_TYPES, VIDEO_TYPES, normalize_upload
from app.pipelines.media import blob_from_upload
from app.providers.types import MediaBlob
from app.schemas.generate import GenerationResult
from app.services.generation import to_generation_result

router = APIRouter(prefix="/generate", tags=["generate"])


async def _optional_blob(
    upload: UploadFile | None,
    *,
    max_bytes: int,
    max_mb: int,
    allowed_types: set[str],
    kind: str,
) -> MediaBlob | None:
    if not upload or not (upload.filename or "").strip():
        return None
    data = await upload.read()
    if len(data) > max_bytes:
        raise UploadTooLargeError(max_mb)
    filename, content_type, payload = normalize_upload(
        upload.filename or "",
        upload.content_type,
        data,
        allowed_types=allowed_types,
        kind=kind,
    )
    return blob_from_upload(filename, content_type, payload)


@router.post("/image", response_model=GenerationResult)
async def generate_image(
    prompt: Annotated[str, Form(min_length=1)],
    image: UploadFile | None = File(None, description="可选参考图，有则图生图"),
    enhance_prompt: bool = Form(False),
    size: str | None = Form(None),
    strength: Annotated[float, Form(ge=0, le=1)] = 0.6,
    async_mode: bool = Form(False),
    container: AppContainer = Depends(get_container),
) -> GenerationResult:
    image_blob = await _optional_blob(
        image,
        max_bytes=container.settings.max_upload_bytes,
        max_mb=container.settings.max_upload_mb,
        allowed_types=IMAGE_TYPES,
        kind="image",
    )
    if image_blob:
        task = await container.generation.image_to_image(
            prompt,
            image_blob,
            enhance_prompt=enhance_prompt,
            size=size,
            strength=strength,
            async_mode=async_mode,
        )
    else:
        task = await container.generation.text_to_image(
            prompt,
            enhance_prompt=enhance_prompt,
            size=size,
            async_mode=async_mode,
        )
    return to_generation_result(task_to_response(task))


@router.post("/video", response_model=GenerationResult)
async def generate_video(
    prompt: Annotated[str, Form(min_length=1)],
    image: UploadFile | None = File(None, description="可选参考图"),
    video: UploadFile | None = File(None, description="可选参考视频"),
    enhance_prompt: bool = Form(False),
    duration_seconds: Annotated[float, Form(ge=2, le=10)] = 5,
    resolution: str = Form("720P"),
    ratio: str = Form("adaptive"),
    async_mode: bool = Form(True),
    container: AppContainer = Depends(get_container),
) -> GenerationResult:
    limits = {
        "max_bytes": container.settings.max_upload_bytes,
        "max_mb": container.settings.max_upload_mb,
    }
    image_blob = await _optional_blob(
        image,
        **limits,
        allowed_types=IMAGE_TYPES,
        kind="image",
    )
    video_blob = await _optional_blob(
        video,
        **limits,
        allowed_types=VIDEO_TYPES,
        kind="video",
    )
    task = await container.generation.generate_video(
        prompt,
        image=image_blob,
        video=video_blob,
        enhance_prompt=enhance_prompt,
        duration_seconds=duration_seconds,
        resolution=resolution,
        ratio=ratio,
        async_mode=async_mode,
    )
    return to_generation_result(task_to_response(task))
