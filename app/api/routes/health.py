from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.container import AppContainer
from app.schemas.common import HealthResponse, ProbeResponse, ProviderInfo

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=ProbeResponse)
async def live() -> ProbeResponse:
    return ProbeResponse(status="ok")


@router.get("/health/ready", response_model=ProbeResponse)
async def ready(container: AppContainer = Depends(get_container)):
    checks: dict[str, str] = {}
    try:
        await container.storage.healthcheck()
        checks["storage"] = container.storage.backend
        await container.tasks.healthcheck()
        checks["tasks"] = container.tasks.backend
        await container.queue.healthcheck()
        checks["queue"] = container.queue.backend
    except Exception as exc:
        body = ProbeResponse(status="not_ready", checks={**checks, "error": str(exc)})
        return JSONResponse(status_code=503, content=body.model_dump())
    return ProbeResponse(status="ok", checks=checks)


@router.get("/v1/health", response_model=HealthResponse)
async def health(container: AppContainer = Depends(get_container)) -> HealthResponse:
    providers = container.providers
    return HealthResponse(
        app=container.settings.app_name,
        env=container.settings.app_env,
        providers={
            "llm": ProviderInfo(
                name=providers.llm.name,
                model=providers.llm.model,
                mocked=providers.llm.mocked,
            ),
            "image": ProviderInfo(
                name=providers.image.name,
                model=providers.image.model,
                mocked=providers.image.mocked,
            ),
            "video": ProviderInfo(
                name=providers.video.name,
                model=providers.video.model,
                mocked=providers.video.mocked,
            ),
        },
    )
