from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigError

AppEnv = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "media-gen-service"
    app_env: AppEnv = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    api_keys: str = ""
    cors_origins: str = "*"
    allow_mock_providers: bool = True
    embedded_worker: bool | None = None
    sync_wait_timeout_seconds: float = 180.0

    llm_provider: str = "openai_compat"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    image_provider: str = "dashscope"
    image_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    image_api_key: str = ""
    image_model: str = "qwen-image-3.0"
    image_size: str = "1024*1024"

    video_provider: str = "dashscope"
    video_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    video_api_key: str = ""
    video_model: str = "wan3.0-video"
    video_image_to_video_path: str = "/v1/video/image-to-video"
    video_video_to_video_path: str = "/v1/video/video-to-video"
    video_task_path: str = "/v1/video/tasks/{task_id}"
    video_poll_interval_seconds: float = 15.0
    video_poll_timeout_seconds: float = 600.0

    storage_backend: Literal["local", "s3"] = "local"
    storage_dir: Path = Field(default=Path("./data/media"))
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    s3_public_base_url: str = ""

    task_backend: Literal["sqlite", "memory"] = "sqlite"
    sqlite_path: Path = Field(default=Path("./data/tasks.db"))

    queue_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://127.0.0.1:6379/0"
    queue_name: str = "media-gen:jobs"

    max_upload_mb: int = 80
    chat_history_limit: int = 20

    @field_validator("app_env")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        return value.lower()

    @field_validator("embedded_worker", mode="before")
    @classmethod
    def empty_embedded_worker(cls, value):
        if value == "":
            return None
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def parsed_api_keys(self) -> set[str]:
        return {item.strip() for item in self.api_keys.split(",") if item.strip()}

    @property
    def api_key_required(self) -> bool:
        return self.is_production or bool(self.parsed_api_keys)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def should_embed_worker(self) -> bool:
        if self.embedded_worker is not None:
            return self.embedded_worker
        return self.app_env == "development" and self.queue_backend == "memory"

    def use_mock_llm(self) -> bool:
        return self.llm_provider == "mock" or (self.allow_mock_providers and not self.llm_api_key)

    @property
    def resolved_image_api_key(self) -> str:
        if self.image_api_key.strip():
            return self.image_api_key.strip()
        if self.image_provider == "dashscope":
            return self.llm_api_key.strip()
        return ""

    def use_mock_image(self) -> bool:
        return self.image_provider == "mock" or (
            self.allow_mock_providers and not self.resolved_image_api_key
        )

    @property
    def resolved_video_api_key(self) -> str:
        if self.video_api_key.strip():
            return self.video_api_key.strip()
        if self.video_provider == "dashscope":
            return self.llm_api_key.strip()
        return ""

    def use_mock_video(self) -> bool:
        if self.video_provider == "mock":
            return True
        if self.video_provider == "dashscope":
            return self.allow_mock_providers and not self.resolved_video_api_key
        return self.allow_mock_providers and (not self.video_api_key or not self.video_base_url)

    def uses_any_mock(self) -> bool:
        return self.use_mock_llm() or self.use_mock_image() or self.use_mock_video()

    def validate_runtime(self, role: str = "api") -> None:
        if not self.is_production:
            if self.queue_backend == "memory" and not self.should_embed_worker and role == "api":
                raise ConfigError("QUEUE_BACKEND=memory 时必须开启 EMBEDDED_WORKER，否则任务不会被消费")
            return

        if self.allow_mock_providers or self.uses_any_mock():
            raise ConfigError("production 禁止 mock provider，请配置真实模型 Key")
        video_ready = bool(self.resolved_video_api_key) and (
            self.video_provider == "dashscope" or bool(self.video_base_url)
        )
        if not self.llm_api_key or not self.resolved_image_api_key or not video_ready:
            raise ConfigError("production 必须配置 LLM / IMAGE / VIDEO 的真实凭证")
        if role == "api" and not self.parsed_api_keys:
            raise ConfigError("production 必须配置 API_KEYS")
        if self.queue_backend != "redis":
            raise ConfigError("production 必须使用 QUEUE_BACKEND=redis")
        if self.should_embed_worker:
            raise ConfigError("production 禁止 EMBEDDED_WORKER，请独立启动 Worker")
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ConfigError("STORAGE_BACKEND=s3 时必须配置 S3_BUCKET")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    get_settings.cache_clear()
