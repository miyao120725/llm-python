from fastapi import APIRouter, Depends

from app.api.deps import require_api_key
from app.api.routes import generate, llm, media, tasks

api_router = APIRouter(dependencies=[Depends(require_api_key)])
api_router.include_router(llm.router)
api_router.include_router(generate.router)
api_router.include_router(tasks.router)
api_router.include_router(media.router)
