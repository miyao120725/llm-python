import asyncio

import httpx

from app.config import Settings
from app.providers.image.dashscope import DashScopeImageProvider, to_dashscope_size
from app.providers.registry import build_providers
from app.providers.types import MediaBlob
from tests.conftest import make_settings


class _FakeImageClient:
    def __init__(self):
        self.posts: list[dict] = []

    async def post(self, path: str, json=None):
        self.posts.append({"path": path, "json": json})
        return httpx.Response(
            200,
            json={
                "output": {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": [{"image": "https://dashscope-result.example/out.png"}],
                            },
                        }
                    ]
                }
            },
            request=httpx.Request("POST", f"https://dashscope.aliyuncs.com/api/v1{path}"),
        )

    async def get(self, url: str):
        return httpx.Response(
            200,
            content=b"\x89PNG\r\n\x1a\nfake",
            request=httpx.Request("GET", url),
        )


def test_to_dashscope_size():
    assert to_dashscope_size("1024x1024") == "1024*1024"
    assert to_dashscope_size("1024*1024") == "1024*1024"


def test_dashscope_generate_and_edit_download():
    fake = _FakeImageClient()
    provider = DashScopeImageProvider(
        base_url="https://dashscope.aliyuncs.com/api/v1",
        api_key="sk-test",
        model="qwen-image-3.0",
        client=fake,
    )

    generated = asyncio.run(provider.generate("一只猫", size="1024x1024"))
    assert generated.data.startswith(b"\x89PNG")
    body = fake.posts[0]["json"]
    assert body["model"] == "qwen-image-3.0"
    assert body["parameters"]["prompt_extend"] is False
    assert body["parameters"]["enable_thinking"] is False
    assert body["parameters"]["size"] == "1024*1024"
    assert body["input"]["messages"][0]["content"] == [{"text": "一只猫"}]

    edited = asyncio.run(
        provider.edit(
            "改成赛博朋克",
            MediaBlob(data=b"abc", filename="cat.png", content_type="image/png"),
        )
    )
    assert edited.data.startswith(b"\x89PNG")
    edit_content = fake.posts[1]["json"]["input"]["messages"][0]["content"]
    assert edit_content[0]["image"].startswith("data:image/png;base64,")
    assert edit_content[1] == {"text": "改成赛博朋克"}


def test_download_error_does_not_leak_signed_url():
    signed = (
        "https://dashscope-result.example/out.png"
        "?OSSAccessKeyId=EXAMPLE&Signature=secret"
    )

    class _Client:
        async def post(self, path: str, json=None):
            return httpx.Response(
                200,
                json={
                    "output": {
                        "choices": [
                            {
                                "message": {
                                    "content": [{"image": signed}],
                                }
                            }
                        ]
                    }
                },
                request=httpx.Request("POST", "https://dashscope.aliyuncs.com/api/v1" + path),
            )

        async def get(self, url: str):
            request = httpx.Request("GET", url)
            response = httpx.Response(403, request=request)
            raise httpx.HTTPStatusError("403", request=request, response=response)

    provider = DashScopeImageProvider(
        base_url="https://dashscope.aliyuncs.com/api/v1",
        api_key="sk-test",
        model="qwen-image-3.0",
        client=_Client(),
    )
    try:
        asyncio.run(provider.generate("猫"))
    except Exception as exc:
        text = str(exc)
        assert "HTTP 403" in text
        assert "Signature" not in text
        assert "OSSAccessKeyId" not in text
    else:
        raise AssertionError("expected ProviderError")


def test_dashscope_error_body():
    class _ErrorClient:
        async def post(self, path: str, json=None):
            return httpx.Response(
                400,
                json={"code": "InvalidParameter", "message": "n must be 1"},
                request=httpx.Request("POST", "https://dashscope.aliyuncs.com/api/v1" + path),
            )

    provider = DashScopeImageProvider(
        base_url="https://dashscope.aliyuncs.com/api/v1",
        api_key="sk-test",
        model="qwen-image-3.0",
        client=_ErrorClient(),
    )
    try:
        asyncio.run(provider.generate("猫"))
    except Exception as exc:
        assert "InvalidParameter" in str(exc)
    else:
        raise AssertionError("expected ProviderError")


def test_registry_uses_dashscope_when_key_present(tmp_path):
    settings = make_settings(
        tmp_path,
        image_provider="dashscope",
        llm_api_key="sk-from-llm",
        image_api_key="",
        allow_mock_providers=True,
    )
    providers = build_providers(settings)
    assert providers.image.name == "dashscope"
    assert providers.image.model == "qwen-image-3.0"
    assert providers.image.mocked is False
    asyncio.run(providers.aclose())


def test_default_image_settings():
    settings = Settings(_env_file=None)
    assert settings.image_provider == "dashscope"
    assert settings.image_model == "qwen-image-3.0"
    assert settings.image_base_url.endswith("/api/v1")
