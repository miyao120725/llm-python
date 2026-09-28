import base64
from urllib.parse import urlparse

import httpx

from app.core.exceptions import ProviderError
from app.providers.image.base import ImageProvider
from app.providers.types import ImageResult, MediaBlob

_GENERATION_PATH = "/services/aigc/multimodal-generation/generation"


def to_dashscope_size(size: str) -> str:
    return size.replace("x", "*").replace("X", "*")


class DashScopeImageProvider(ImageProvider):
    name = "dashscope"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        default_size: str = "1024*1024",
        timeout: float = 180.0,
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(model)
        self.default_size = default_size
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        # OSS 预签名 URL 不能带 Bearer，否则 403
        self._download_client = client or httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        )

    async def generate(self, prompt: str, *, size: str | None = None) -> ImageResult:
        return await self._generate([{"text": prompt}], size=size)

    async def edit(
        self,
        prompt: str,
        image: MediaBlob,
        *,
        size: str | None = None,
        strength: float = 0.6,
    ) -> ImageResult:
        return await self._generate(
            [
                {"image": _as_data_uri(image)},
                {"text": prompt},
            ],
            size=size,
        )

    async def _generate(self, content: list[dict], *, size: str | None) -> ImageResult:
        payload = {
            "model": self.model,
            "input": {"messages": [{"role": "user", "content": content}]},
            "parameters": {
                "prompt_extend": False,
                "enable_thinking": False,
                "watermark": False,
                "n": 1,
                "size": to_dashscope_size(size or self.default_size),
            },
        }
        try:
            response = await self._client.post(_GENERATION_PATH, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"文生图请求失败: {exc}") from exc

        data = _safe_json(response)
        if response.status_code >= 400 or data.get("code"):
            message = data.get("message") or response.reason_phrase
            raise ProviderError(
                f"图像请求失败: HTTP {response.status_code} {data.get('code', '')} {message}".strip()
            )

        image_url = _first_image_url(data)
        image_bytes = await self._download(image_url)
        return ImageResult(data=image_bytes, content_type="image/png", raw=data)

    async def _download(self, url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ProviderError("模型返回了非法下载地址")
        try:
            response = await self._download_client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"下载生成结果失败: HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("下载生成结果失败") from exc
        return response.content

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
            await self._download_client.aclose()


def _as_data_uri(image: MediaBlob) -> str:
    mime = image.content_type or "image/png"
    encoded = base64.b64encode(image.data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _safe_json(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError(f"图像响应不是 JSON: HTTP {response.status_code}") from exc
    return data if isinstance(data, dict) else {}


def _first_image_url(data: dict) -> str:
    try:
        content = data["output"]["choices"][0]["message"]["content"]
        for item in content:
            url = item.get("image")
            if url:
                return url
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    raise ProviderError("图像响应缺少生成地址")
