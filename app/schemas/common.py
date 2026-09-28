from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class MediaRef(BaseModel):
    file_id: str
    filename: str
    content_type: str
    url: str
    size: int = 0


class ProviderInfo(BaseModel):
    name: str
    model: str = ""
    mocked: bool = False


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    env: str
    providers: dict[str, ProviderInfo]


class ProbeResponse(BaseModel):
    status: str
    checks: dict[str, str] = {}
