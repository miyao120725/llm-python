from app.providers.image.base import ImageProvider
from app.providers.types import ImageResult, MediaBlob

# 1x1 透明 PNG，便于无 Key 时把整条链路跑通
_MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8cfc000000101010018dd8d180000000049454e44ae426082"
)


class MockImageProvider(ImageProvider):
    name = "mock"
    mocked = True

    async def generate(self, prompt: str, *, size: str | None = None) -> ImageResult:
        return ImageResult(
            data=_MINIMAL_PNG,
            content_type="image/png",
            raw={"prompt": prompt, "size": size, "provider": "mock"},
        )

    async def edit(
        self,
        prompt: str,
        image: MediaBlob,
        *,
        size: str | None = None,
        strength: float = 0.6,
    ) -> ImageResult:
        return ImageResult(
            data=_MINIMAL_PNG,
            content_type="image/png",
            raw={
                "prompt": prompt,
                "size": size,
                "strength": strength,
                "source": image.filename,
                "provider": "mock",
            },
        )
