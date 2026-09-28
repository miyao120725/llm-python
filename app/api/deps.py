from fastapi import Request

from app.container import AppContainer
from app.core.exceptions import UnauthorizedError


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


async def require_api_key(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.api_key_required:
        return
    incoming = request.headers.get("X-API-Key", "")
    if incoming not in settings.parsed_api_keys:
        raise UnauthorizedError()
