from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.api.mappers import task_to_response
from app.container import AppContainer
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, container: AppContainer = Depends(get_container)) -> TaskResponse:
    task = await container.generation.get_task(task_id)
    return task_to_response(task)
