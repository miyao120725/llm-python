import re

from app.core.exceptions import InvalidUploadError, MediaNotFoundError

FILE_ID_RE = re.compile(r"^[a-f0-9]{32}\.[A-Za-z0-9]{1,8}$")

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}

SUFFIX_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


def validate_file_id(file_id: str) -> str:
    if not FILE_ID_RE.match(file_id):
        raise MediaNotFoundError(file_id)
    return file_id


def guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    return SUFFIX_TYPES.get(suffix, fallback)


def normalize_upload(
    filename: str,
    content_type: str | None,
    data: bytes,
    *,
    allowed_types: set[str],
    kind: str,
) -> tuple[str, str, bytes]:
    if not data:
        raise InvalidUploadError(f"{kind} 文件不能为空")
    resolved_name = filename or f"upload.{kind}"
    resolved_type = (content_type or "").split(";")[0].strip().lower()
    if resolved_type in {"", "application/octet-stream"}:
        resolved_type = guess_content_type(resolved_name)
    if resolved_type == "image/jpg":
        resolved_type = "image/jpeg"
    if resolved_type not in allowed_types:
        raise InvalidUploadError(f"{kind} 仅支持 {', '.join(sorted(allowed_types))}")
    return resolved_name, resolved_type, data
