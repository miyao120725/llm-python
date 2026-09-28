import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_settings(tmp_path, **overrides) -> Settings:
    values = {
        "app_env": "development",
        "allow_mock_providers": True,
        "llm_provider": "mock",
        "image_provider": "mock",
        "video_provider": "mock",
        "queue_backend": "memory",
        "embedded_worker": True,
        "task_backend": "sqlite",
        "sqlite_path": tmp_path / "tasks.db",
        "storage_backend": "local",
        "storage_dir": tmp_path / "media",
        "api_keys": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
