import asyncio

import httpx

from app.config import Settings
from app.providers.registry import build_providers
from app.providers.types import MediaBlob
from app.providers.video.dashscope import DashScopeVideoProvider
from tests.conftest import make_settings


class _FakeVideoClient:
    def __init__(self):
        self.posts: list[dict] = []
        self.gets: list[str] = []

    async def post(self, path: str, json=None, headers=None, files=None):
        self.posts.append({"path": path, "json": json, "headers": headers or {}, "files": files})
        if files:
            return httpx.Response(200, request=httpx.Request("POST", str(path)))
        return httpx.Response(
            200,
            json={"output": {"task_id": "task-1", "task_status": "PENDING"}},
            request=httpx.Request("POST", f"https://dashscope.aliyuncs.com/api/v1{path}"),
        )

    async def get(self, path: str, params=None):
        self.gets.append(str(path))
        if str(path).startswith("http"):
            return httpx.Response(
                200,
                content=b"mock-mp4-bytes",
                request=httpx.Request("GET", str(path)),
            )
        if "uploads" in str(path):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "upload_dir": "dashscope-instant/demo",
                        "upload_host": "https://oss.example/upload",
                        "oss_access_key_id": "id",
                        "signature": "sig",
                        "policy": "pol",
                        "x_oss_object_acl": "private",
                        "x_oss_forbid_overwrite": "true",
                    }
                },
                request=httpx.Request("GET", "https://dashscope.aliyuncs.com/api/v1/uploads"),
            )
        return httpx.Response(
            200,
            json={
                "output": {
                    "task_id": "task-1",
                    "task_status": "SUCCEEDED",
                    "video_url": "https://dashscope-result.example/out.mp4",
                }
            },
            request=httpx.Request("GET", f"https://dashscope.aliyuncs.com/api/v1{path}"),
        )


def test_dashscope_text_and_combo_video():
    fake = _FakeVideoClient()
    provider = DashScopeVideoProvider(
        base_url="https://dashscope.aliyuncs.com/api/v1",
        api_key="sk-test",
        model="wan3.0-video",
        poll_interval=0,
        client=fake,
    )

    text = asyncio.run(provider.synthesize(prompt="小猫奔跑", duration_seconds=6))
    assert text.data == b"mock-mp4-bytes"
    body = fake.posts[0]["json"]
    assert body["model"] == "wan3.0-video"
    assert body["parameters"]["duration"] == 6
    assert body["parameters"]["prompt_extend"] is False
    assert "media" not in body["input"]
    assert fake.posts[0]["headers"]["X-DashScope-Async"] == "enable"

    combo = asyncio.run(
        provider.synthesize(
            prompt="按图1和视频1继续",
            image=MediaBlob(data=b"img", filename="a.png", content_type="image/png"),
            video=MediaBlob(data=b"vid", filename="b.mp4", content_type="video/mp4"),
        )
    )
    assert combo.data == b"mock-mp4-bytes"
    combo_body = [item["json"] for item in fake.posts if item["json"]][-1]
    types = [item["type"] for item in combo_body["input"]["media"]]
    assert types == ["reference_image", "reference_video"]
    assert combo_body["input"]["media"][1]["url"].startswith("oss://")


def test_registry_uses_dashscope_video(tmp_path):
    settings = make_settings(
        tmp_path,
        video_provider="dashscope",
        llm_api_key="sk-from-llm",
        video_api_key="",
        allow_mock_providers=True,
    )
    providers = build_providers(settings)
    assert providers.video.name == "dashscope"
    assert providers.video.model == "wan3.0-video"
    assert providers.video.mocked is False
    asyncio.run(providers.aclose())


def test_default_video_settings():
    settings = Settings(_env_file=None)
    assert settings.video_provider == "dashscope"
    assert settings.video_model == "wan3.0-video"
