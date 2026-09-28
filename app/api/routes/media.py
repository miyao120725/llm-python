from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse

from app.api.deps import get_container
from app.container import AppContainer
from app.core.exceptions import MediaNotFoundError
from app.core.files import guess_content_type, validate_file_id

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{file_id}")
async def get_media(file_id: str, container: AppContainer = Depends(get_container)):
    validate_file_id(file_id)
    path = await container.storage.local_path(file_id)
    if path is not None:
        return FileResponse(path, media_type=guess_content_type(file_id), filename=file_id)
    url = await container.storage.presigned_url(file_id)
    if not url:
        raise MediaNotFoundError(file_id)
    return RedirectResponse(url)
