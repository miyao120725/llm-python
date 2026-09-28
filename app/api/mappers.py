from app.domain.models import MediaObject, TaskRecord
from app.schemas.common import MediaRef
from app.schemas.task import TaskResponse


def media_to_ref(media: MediaObject | None) -> MediaRef | None:
    if media is None:
        return None
    return MediaRef(
        file_id=media.file_id,
        filename=media.filename,
        content_type=media.content_type,
        url=media.url,
        size=media.size,
    )


def task_to_response(task: TaskRecord) -> TaskResponse:
    return TaskResponse(
        task_id=task.task_id,
        kind=task.kind,
        status=task.status.value,
        prompt=task.prompt,
        enhanced_prompt=task.enhanced_prompt,
        media=media_to_ref(task.media),
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
