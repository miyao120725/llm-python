import base64

import httpx

from app.core.exceptions import ProviderError
from app.providers.image.base import ImageProvider
from app.providers.types import ImageResult, MediaBlob


class OpenAICompatImageProvider(ImageProvider):
    name = "openai_compat"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        default_size: str = "1024x1024",
        timeout: float = 120.0,
    ):
        super().__init__(model)
        self.default_size = default_size
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate(self, prompt: str, *, size: str | None = None) -> ImageResult:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size or self.default_size,
            "response_format": "b64_json",
        }
        try:
            response = await self._client.post("/images/generations", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"文生图请求失败: {exc}") from exc

        data = response.json()
        try:
            item = data["data"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"文生图响应格式无法解析: {data}") from exc

        if item.get("b64_json"):
            return ImageResult(
                data=base64.b64decode(item["b64_json"]),
                content_type="image/png",
                raw=data,
            )
        if item.get("url"):
            return ImageResult(url=item["url"], content_type="image/png", raw=data)
        raise ProviderError(f"文生图响应缺少图像数据: {data}")

    async def edit(
        self,
        prompt: str,
        image: MediaBlob,
        *,
        size: str | None = None,
        strength: float = 0.6,
    ) -> ImageResult:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": "1",
            "size": size or self.default_size,
            "response_format": "b64_json",
        }
        files = {
            "image": (
                image.filename or "image.png",
                image.data,
                image.content_type or "image/png",
            )
        }
        try:
            response = await self._client.post(
                "/images/edits",
                data=payload,
                files=files,
                headers={"Content-Type": None},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"图生图请求失败: {exc}") from exc

        data = response.json()
        try:
            item = data["data"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"图生图响应格式无法解析: {data}") from exc

        if item.get("b64_json"):
            return ImageResult(
                data=base64.b64decode(item["b64_json"]),
                content_type="image/png",
                raw=data,
            )
        if item.get("url"):
            return ImageResult(url=item["url"], content_type="image/png", raw=data)
        raise ProviderError(f"图生图响应缺少图像数据: {data}")

    async def aclose(self) -> None:
        await self._client.aclose()
