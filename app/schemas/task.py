from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import MediaRef


class TaskResponse(BaseModel):
    task_id: str
    kind: str
    status: str
    prompt: str
    enhanced_prompt: str | None = None
    media: MediaRef | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
