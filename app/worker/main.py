import asyncio
import logging

from app.config import get_settings
from app.container import build_container
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


async def _serve() -> None:
    settings = get_settings()
    setup_logging(debug=settings.app_debug, json_logs=True)
    settings.validate_runtime(role="worker")
    container = await build_container(settings)
    try:
        await container.worker.run_forever()
    finally:
        await container.aclose()


def run() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    run()
