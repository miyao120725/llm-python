from ipaddress import ip_address
from urllib.parse import urlparse

import httpx

from app.core.exceptions import ProviderError
from app.core.files import SUFFIX_TYPES, guess_content_type
from app.domain.models import MediaObject
from app.ports.storage import ObjectStorage
from app.providers.types import ImageResult, MediaBlob, VideoResult


def suffix_from_content_type(content_type: str, fallback: str) -> str:
    mapping = {value: key for key, value in SUFFIX_TYPES.items()}
    mapping["image/jpg"] = ".jpg"
    return mapping.get(content_type, fallback)


def _is_blocked_host(host: str) -> bool:
    hostname = host.split("%")[0]
    try:
        ip = ip_address(hostname)
    except ValueError:
        return hostname in {"localhost", "metadata.google.internal"}
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ProviderError("模型返回了非法下载地址")
    if _is_blocked_host(parsed.hostname):
        raise ProviderError("拒绝下载内网或本地地址")


async def persist_remote_or_bytes(
    storage: ObjectStorage,
    *,
    data: bytes | None,
    url: str | None,
    content_type: str,
    fallback_suffix: str,
) -> MediaObject:
    if data:
        return await storage.save_bytes(
            data,
            suffix=suffix_from_content_type(content_type, fallback_suffix),
            content_type=content_type,
        )
    if not url:
        raise ProviderError("模型未返回文件内容或可下载地址")

    assert_public_url(url)
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderError(f"下载生成结果失败: {exc}") from exc

    resolved_type = response.headers.get("content-type", content_type).split(";")[0]
    return await storage.save_bytes(
        response.content,
        suffix=suffix_from_content_type(resolved_type, fallback_suffix),
        content_type=resolved_type,
    )


async def persist_image(storage: ObjectStorage, result: ImageResult) -> MediaObject:
    return await persist_remote_or_bytes(
        storage,
        data=result.data,
        url=result.url,
        content_type=result.content_type,
        fallback_suffix=".png",
    )


async def persist_video(storage: ObjectStorage, result: VideoResult) -> MediaObject:
    return await persist_remote_or_bytes(
        storage,
        data=result.data,
        url=result.url,
        content_type=result.content_type,
        fallback_suffix=".mp4",
    )


def blob_from_upload(filename: str, content_type: str, data: bytes) -> MediaBlob:
    return MediaBlob(
        data=data,
        filename=filename or "upload.bin",
        content_type=content_type or "application/octet-stream",
    )


def content_type_of(path_or_name: str) -> str:
    return guess_content_type(path_or_name)
