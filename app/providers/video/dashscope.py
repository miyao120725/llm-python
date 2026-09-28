import asyncio
import base64
import time
from urllib.parse import urlparse

import httpx

from app.core.exceptions import ProviderError
from app.providers.types import MediaBlob, VideoResult
from app.providers.video.base import VideoProvider

_SYNTHESIS_PATH = "/services/aigc/video-generation/video-synthesis"


class DashScopeVideoProvider(VideoProvider):
    name = "dashscope"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        poll_interval: float = 15.0,
        poll_timeout: float = 600.0,
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(model)
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        self._download_client = client or httpx.AsyncClient(
            timeout=180.0,
            follow_redirects=True,
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
        media: list[dict] = []
        headers = {"X-DashScope-Async": "enable"}
        if image and video:
            media.append({"type": "reference_image", "url": _as_data_uri(image)})
            oss_url = await self._upload_video(video)
            media.append({"type": "reference_video", "url": oss_url})
            headers["X-DashScope-OssResourceResolve"] = "enable"
        elif image:
            media.append({"type": "first_frame", "url": _as_data_uri(image)})
        elif video:
            oss_url = await self._upload_video(video)
            media.append({"type": "reference_video", "url": oss_url})
            headers["X-DashScope-OssResourceResolve"] = "enable"

        payload: dict = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {
                "resolution": resolution,
                "ratio": ratio,
                "duration": int(round(duration_seconds)),
                "prompt_extend": False,
                "watermark": False,
            },
        }
        if media:
            payload["input"]["media"] = media

        try:
            response = await self._client.post(_SYNTHESIS_PATH, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError("视频生成请求失败") from exc

        data = _safe_json(response)
        if response.status_code >= 400 or data.get("code"):
            raise ProviderError(
                f"视频请求失败: HTTP {response.status_code} {data.get('code', '')} {_short(data.get('message'))}".strip()
            )
        task_id = (data.get("output") or {}).get("task_id")
        if not task_id:
            raise ProviderError("视频响应缺少 task_id")
        return await self._poll(str(task_id))

    async def _upload_video(self, video: MediaBlob) -> str:
        try:
            policy_resp = await self._client.get(
                "/uploads",
                params={"action": "getPolicy", "model": self.model},
            )
        except httpx.HTTPError as exc:
            raise ProviderError("获取视频上传凭证失败") from exc
        policy_body = _safe_json(policy_resp)
        if policy_resp.status_code >= 400 or policy_body.get("code"):
            raise ProviderError("获取视频上传凭证失败")
        policy = policy_body.get("data") or {}
        upload_dir = policy.get("upload_dir")
        upload_host = policy.get("upload_host")
        if not upload_dir or not upload_host:
            raise ProviderError("视频上传凭证格式无法解析")
        filename = video.filename or "clip.mp4"
        key = f"{upload_dir}/{filename}"
        files = {
            "OSSAccessKeyId": (None, policy.get("oss_access_key_id", "")),
            "Signature": (None, policy.get("signature", "")),
            "policy": (None, policy.get("policy", "")),
            "x-oss-object-acl": (None, policy.get("x_oss_object_acl", "")),
            "x-oss-forbid-overwrite": (None, policy.get("x_oss_forbid_overwrite", "")),
            "key": (None, key),
            "success_action_status": (None, "200"),
            "file": (filename, video.data, video.content_type or "video/mp4"),
        }
        try:
            uploaded = await self._download_client.post(upload_host, files=files)
            uploaded.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError("上传参考视频失败") from exc
        return f"oss://{key}"

    async def _poll(self, task_id: str) -> VideoResult:
        deadline = time.monotonic() + self.poll_timeout
        while time.monotonic() < deadline:
            try:
                response = await self._client.get(f"/tasks/{task_id}")
            except httpx.HTTPError as exc:
                raise ProviderError("视频任务查询失败") from exc
            data = _safe_json(response)
            output = data.get("output") or {}
            status = str(output.get("task_status") or "").upper()
            if status == "FAILED":
                raise ProviderError(
                    f"视频任务失败: {output.get('code', '')} {_short(output.get('message'))}".strip()
                )
            if status == "SUCCEEDED":
                video_url = output.get("video_url")
                if not video_url:
                    raise ProviderError("视频任务成功但缺少地址")
                content = await self._download(str(video_url))
                return VideoResult(data=content, content_type="video/mp4", raw=data)
            if status in {"CANCELED", "UNKNOWN"}:
                raise ProviderError(f"视频任务状态异常: {status}")
            await asyncio.sleep(self.poll_interval)
        raise ProviderError("视频任务超时")

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
        raise ProviderError(f"视频响应不是 JSON: HTTP {response.status_code}") from exc
    return data if isinstance(data, dict) else {}


def _short(message: object) -> str:
    text = str(message or "")
    return text[:160]
