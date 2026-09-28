import asyncio
import time
from typing import Any

import httpx

from app.core.exceptions import ProviderError
from app.providers.types import MediaBlob, VideoResult
from app.providers.video.base import VideoProvider


class HttpVideoProvider(VideoProvider):
    """通用 HTTP 视频模型适配器。

    约定厂商接口尽量贴近：
    - POST {base_url}{image_to_video_path}  multipart: prompt + image
    - POST {base_url}{video_to_video_path}  multipart: prompt + video
    - 同步返回 video_url / video_b64，或返回 task_id 后轮询 GET {task_path}
    """

    name = "http"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str = "",
        image_to_video_path: str,
        video_to_video_path: str,
        task_path: str,
        poll_interval: float = 2.0,
        poll_timeout: float = 180.0,
        timeout: float = 60.0,
    ):
        super().__init__(model)
        self.image_to_video_path = image_to_video_path
        self.video_to_video_path = video_to_video_path
        self.task_path = task_path
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def synthesize(
        self,
        *,
        prompt: str,
        image: MediaBlob | None = None,
        video: MediaBlob | None = None,
        duration_seconds: float = 5,
        resolution: str = "720P",
        ratio: str = "adaptive",
    ) -> VideoResult:
        if image and video:
            raise ProviderError("当前 HTTP 视频厂商不支持同时传入图和视频")
        if image:
            return await self.image_to_video(
                prompt=prompt,
                image=image,
                duration_seconds=duration_seconds,
            )
        if video:
            return await self.video_to_video(prompt=prompt, video=video)
        raise ProviderError("当前 HTTP 视频厂商不支持纯文生视频")

    async def image_to_video(
        self,
        *,
        prompt: str,
        image: MediaBlob,
        duration_seconds: float = 4,
    ) -> VideoResult:
        data = {
            "prompt": prompt,
            "duration": str(duration_seconds),
        }
        if self.model:
            data["model"] = self.model
        files = {
            "image": (image.filename, image.data, image.content_type),
        }
        return await self._submit_and_wait(self.image_to_video_path, data=data, files=files)

    async def video_to_video(
        self,
        *,
        prompt: str,
        video: MediaBlob,
        strength: float = 0.6,
    ) -> VideoResult:
        data = {
            "prompt": prompt,
            "strength": str(strength),
        }
        if self.model:
            data["model"] = self.model
        files = {
            "video": (video.filename, video.data, video.content_type),
        }
        return await self._submit_and_wait(self.video_to_video_path, data=data, files=files)

    async def _submit_and_wait(
        self,
        path: str,
        *,
        data: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
    ) -> VideoResult:
        try:
            response = await self._client.post(path, data=data, files=files)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"视频生成请求失败: {exc}") from exc

        payload = self._safe_json(response)
        result = self._parse_result(payload)
        if result.data or result.url:
            return result
        if result.provider_task_id:
            return await self._poll(result.provider_task_id)
        raise ProviderError(f"视频生成响应缺少结果或 task_id: {payload}")

    async def _poll(self, task_id: str) -> VideoResult:
        deadline = time.monotonic() + self.poll_timeout
        path = self.task_path.format(task_id=task_id)
        while time.monotonic() < deadline:
            try:
                response = await self._client.get(path)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderError(f"视频任务查询失败: {exc}") from exc

            payload = self._safe_json(response)
            status = str(payload.get("status", "")).lower()
            if status in {"failed", "error"}:
                raise ProviderError(payload.get("error") or f"视频任务失败: {payload}")
            result = self._parse_result(payload)
            if status in {"succeeded", "success", "completed"} or result.data or result.url:
                if result.data or result.url:
                    return result
            await asyncio.sleep(self.poll_interval)
        raise ProviderError(f"视频任务超时: {task_id}")

    def _parse_result(self, payload: dict[str, Any]) -> VideoResult:
        data_bytes = None
        b64_value = payload.get("video_b64") or payload.get("b64_json")
        if b64_value:
            import base64

            data_bytes = base64.b64decode(b64_value)

        url = payload.get("video_url") or payload.get("url")
        if not url and isinstance(payload.get("data"), dict):
            url = payload["data"].get("video_url") or payload["data"].get("url")

        task_id = payload.get("task_id") or payload.get("id")
        return VideoResult(
            data=data_bytes,
            url=url,
            provider_task_id=str(task_id) if task_id else None,
            raw=payload,
        )

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"视频服务返回了非 JSON: {response.text[:200]}") from exc
        if not isinstance(data, dict):
            raise ProviderError(f"视频服务返回了非对象 JSON: {data}")
        return data

    async def aclose(self) -> None:
        await self._client.aclose()
