import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.exceptions import ConfigError
from app.main import create_app
from tests.conftest import make_settings


def test_api_key_required_when_configured(tmp_path):
    settings = make_settings(tmp_path, api_keys="dev-secret")
    with TestClient(create_app(settings)) as client:
        denied = client.post(
            "/v1/generate/image",
            data={"prompt": "猫", "async_mode": "false"},
        )
        assert denied.status_code == 401
        assert denied.json()["code"] == "unauthorized"

        allowed = client.post(
            "/v1/generate/image",
            headers={"X-API-Key": "dev-secret"},
            data={"prompt": "猫", "async_mode": "false"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "succeeded"

        live = client.get("/health/live")
        assert live.status_code == 200


def test_production_rejects_mock_and_memory_queue():
    settings = Settings(
        _env_file=None,
        app_env="production",
        allow_mock_providers=True,
        api_keys="prod-key",
        queue_backend="memory",
        embedded_worker=True,
    )
    with pytest.raises(ConfigError, match="production"):
        settings.validate_runtime(role="api")


def test_production_dashscope_can_reuse_llm_key():
    settings = Settings(
        _env_file=None,
        app_env="production",
        allow_mock_providers=False,
        api_keys="prod-key",
        queue_backend="redis",
        embedded_worker=False,
        llm_api_key="sk-llm",
        image_provider="dashscope",
        image_api_key="",
        video_provider="dashscope",
        video_api_key="",
        video_base_url="https://dashscope.aliyuncs.com/api/v1",
    )
    settings.validate_runtime(role="api")
    assert settings.resolved_image_api_key == "sk-llm"
    assert settings.resolved_video_api_key == "sk-llm"
    assert settings.use_mock_image() is False
    assert settings.use_mock_video() is False


def test_memory_queue_without_worker_is_rejected(tmp_path):
    settings = make_settings(tmp_path, embedded_worker=False, queue_backend="memory")
    with pytest.raises(ConfigError, match="EMBEDDED_WORKER"):
        settings.validate_runtime(role="api")
