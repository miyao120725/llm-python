from app.providers.types import MediaBlob, VideoResult
from app.providers.video.base import VideoProvider

# 极小占位文件，仅用于打通本地链路，不是可播放成片
_PLACEHOLDER_MP4 = b"mock-mp4-placeholder"


class MockVideoProvider(VideoProvider):
    name = "mock"
    mocked = True

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
            mode = "image_and_video_to_video"
        elif image:
            mode = "image_to_video"
        elif video:
            mode = "video_to_video"
        else:
            mode = "text_to_video"
        return VideoResult(
            data=_PLACEHOLDER_MP4,
            content_type="video/mp4",
            raw={
                "mode": mode,
                "prompt": prompt,
                "image": image.filename if image else None,
                "video": video.filename if video else None,
                "duration_seconds": duration_seconds,
                "resolution": resolution,
                "ratio": ratio,
            },
        )
