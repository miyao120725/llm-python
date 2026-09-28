import asyncio
import uuid
from typing import Any

from app.core.exceptions import ConfigError, MediaNotFoundError, ProviderError
from app.core.files import validate_file_id
from app.domain.models import MediaObject
from app.ports.storage import ObjectStorage


class S3ObjectStorage(ObjectStorage):
    backend = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str,
        endpoint_url: str = "",
        public_base_url: str = "",
    ):
        try:
            import boto3
        except ImportError as exc:
            raise ConfigError("STORAGE_BACKEND=s3 需要安装 boto3：pip install .[s3]") from exc

        if not bucket:
            raise ConfigError("S3_BUCKET 不能为空")

        kwargs: dict[str, Any] = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._client = boto3.client("s3", **kwargs)
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")

    async def save_bytes(self, data: bytes, *, suffix: str, content_type: str) -> MediaObject:
        file_id = f"{uuid.uuid4().hex}{suffix}"
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=file_id,
            Body=data,
            ContentType=content_type,
        )
        return MediaObject(
            file_id=file_id,
            filename=file_id,
            content_type=content_type,
            url=self._public_url(file_id),
            size=len(data),
        )

    async def get_bytes(self, file_id: str) -> bytes:
        validate_file_id(file_id)
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self.bucket,
                Key=file_id,
            )
        except Exception as exc:
            raise MediaNotFoundError(file_id) from exc
        return await asyncio.to_thread(response["Body"].read)

    async def presigned_url(self, file_id: str) -> str | None:
        validate_file_id(file_id)
        if self.public_base_url:
            return self._public_url(file_id)
        try:
            return await asyncio.to_thread(
                self._client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.bucket, "Key": file_id},
                ExpiresIn=3600,
            )
        except Exception as exc:
            raise ProviderError(f"生成签名 URL 失败: {exc}") from exc

    async def healthcheck(self) -> None:
        await asyncio.to_thread(self._client.head_bucket, Bucket=self.bucket)

    def _public_url(self, file_id: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/{file_id}"
        return f"/v1/media/{file_id}"
