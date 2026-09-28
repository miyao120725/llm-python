from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import Settings
from app.infrastructure.factory import (
    build_conversation_store,
    build_queue,
    build_storage,
    build_task_store,
)
from app.pipelines.image_to_image import ImageToImagePipeline
from app.pipelines.text_to_image import TextToImagePipeline
from app.pipelines.video_generate import VideoGeneratePipeline
from app.ports.conversations import ConversationStore
from app.ports.queue import JobQueue
from app.ports.storage import ObjectStorage
from app.ports.tasks import TaskStore
from app.providers.registry import Providers, build_providers
from app.services.conversation import ConversationService
from app.services.generation import GenerationService
from app.worker.runner import Worker

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    settings: Settings
    providers: Providers
    storage: ObjectStorage
    tasks: TaskStore
    queue: JobQueue
    generation: GenerationService
    conversations: ConversationService
    conversation_store: ConversationStore
    worker: Worker
    embedded_worker_task: asyncio.Task | None = None

    async def aclose(self) -> None:
        if self.embedded_worker_task:
            self.worker.stop()
            self.embedded_worker_task.cancel()
            try:
                await self.embedded_worker_task
            except asyncio.CancelledError:
                pass
        await self.conversation_store.aclose()
        await self.queue.aclose()
        await self.tasks.aclose()
        await self.storage.aclose()
        await self.providers.aclose()


async def build_container(settings: Settings) -> AppContainer:
    providers = build_providers(settings)
    storage = build_storage(settings)
    tasks = build_task_store(settings)
    queue = build_queue(settings)
    text_to_image = TextToImagePipeline(providers.llm, providers.image, storage)
    image_to_image = ImageToImagePipeline(providers.llm, providers.image, storage)
    video_generate = VideoGeneratePipeline(providers.llm, providers.video, storage)
    worker = Worker(
        queue=queue,
        tasks=tasks,
        storage=storage,
        text_to_image=text_to_image,
        image_to_image=image_to_image,
        video_generate=video_generate,
    )
    generation = GenerationService(
        tasks=tasks,
        queue=queue,
        storage=storage,
        wait_timeout=settings.sync_wait_timeout_seconds,
        video_wait_timeout=settings.video_poll_timeout_seconds,
    )
    conversation_store = build_conversation_store(settings)
    conversations = ConversationService(
        store=conversation_store,
        llm=providers.llm,
        history_limit=settings.chat_history_limit,
    )
    return AppContainer(
        settings=settings,
        providers=providers,
        storage=storage,
        tasks=tasks,
        queue=queue,
        generation=generation,
        conversations=conversations,
        conversation_store=conversation_store,
        worker=worker,
    )


async def start_runtime(settings: Settings) -> AppContainer:
    settings.validate_runtime(role="api")
    if settings.uses_any_mock():
        logger.warning("当前使用 mock provider，生成结果仅用于联调，不会调用真实模型")
    container = await build_container(settings)
    if settings.should_embed_worker:
        container.embedded_worker_task = asyncio.create_task(
            container.worker.run_forever(),
            name="embedded-worker",
        )
        logger.info("embedded worker started")
    return container
