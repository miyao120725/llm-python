from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware import RequestIdMiddleware
from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.config import Settings, get_settings
from app.container import start_runtime
from app.core.context import get_request_id
from app.core.exceptions import AppError
from app.core.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setup_logging(debug=resolved.app_debug, json_logs=True)
        app.state.settings = resolved
        app.state.container = await start_runtime(resolved)
        yield
        await app.state.container.aclose()

    app = FastAPI(
        title=resolved.app_name,
        description="提示词生成图片、图片+提示词生成视频、视频生成视频，并接入大模型。",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    origins = resolved.parsed_cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router)
    app.include_router(api_router, prefix="/v1")

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": get_request_id(),
            },
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug and settings.app_env == "development",
    )


if __name__ == "__main__":
    run()
