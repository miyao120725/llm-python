from pydantic import BaseModel, Field

from app.schemas.common import MediaRef


class ImageGenerateForm(BaseModel):
    prompt: str = Field(min_length=1, description="提示词；有参考图时表示如何改图")
    enhance_prompt: bool = Field(default=False, description="是否先用大模型扩写提示词")
    size: str | None = None
    strength: float = Field(default=0.6, ge=0, le=1, description="对原图的改动强度，文生图忽略")
    async_mode: bool = Field(default=False, description="是否异步提交任务")


class VideoGenerateForm(BaseModel):
    prompt: str = Field(min_length=1, description="视频提示词")
    enhance_prompt: bool = False
    duration_seconds: float = Field(default=5, ge=2, le=10)
    resolution: str = Field(default="720P")
    ratio: str = Field(default="adaptive")
    async_mode: bool = True


class GenerationResult(BaseModel):
    task_id: str
    kind: str
    status: str
    prompt: str
    enhanced_prompt: str | None = None
    media: MediaRef | None = None
    error: str | None = None
