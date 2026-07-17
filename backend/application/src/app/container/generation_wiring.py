from datetime import datetime, timedelta, timezone
from typing import AsyncIterator
from uuid import UUID

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from generation.generate_document import GenerateDocument
from generation.get_generation import GetGeneration
from generation.list_generations import ListGenerations
from generation.request_generation import RequestGeneration
from generation.requeue_stale_generations import RequeueStaleGenerations

from container.runtime import create_provider, session_factory, stale_after_minutes


class NoOpGenerationQueue:
    """No dedicated job queue — a submitted generation runs inline via FastAPI
    BackgroundTasks. Durability against a worker crash/restart between enqueue
    and execution is provided by the periodic sweep (run_stale_generation_sweep),
    which resets stuck rows to pending and re-triggers execution — not by this
    queue itself.
    """

    async def enqueue(self, generation_id: UUID) -> None:
        pass


async def create_request_generation() -> AsyncIterator[RequestGeneration]:
    session = session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        yield RequestGeneration(storage=storage, queue=NoOpGenerationQueue())
    finally:
        await session.close()


class _BackgroundGenerateDocument:
    """Dependency-injected into the request scope, but its session is opened
    and closed per `execute()` call — the request's own session is already
    closed by the time BackgroundTasks runs `execute` after the response is
    sent, so it cannot be reused here.
    """

    async def execute(self, generation_id: UUID, owner_id: UUID) -> None:
        session = session_factory()
        try:
            storage = SqlAlchemyGenerationStorage(session)
            usecase = GenerateDocument(storage=storage, provider=create_provider())
            await usecase.execute(generation_id, owner_id)
        finally:
            await session.close()


def create_generate_document() -> GenerateDocument:
    return _BackgroundGenerateDocument()


async def create_get_generation() -> AsyncIterator[GetGeneration]:
    session = session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        yield GetGeneration(storage=storage)
    finally:
        await session.close()


async def create_list_generations() -> AsyncIterator[ListGenerations]:
    session = session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        yield ListGenerations(storage=storage)
    finally:
        await session.close()


async def run_stale_generation_sweep() -> None:
    """Recovers generations stuck in pending/in_progress after a worker crash
    or restart, since NoOpGenerationQueue is not durable across process
    boundaries. Resets each stale row to pending, then re-triggers execution
    the same way the request path does.
    """
    session = session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        usecase = RequeueStaleGenerations(storage=storage)
        older_than = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes())
        requeued = await usecase.execute(older_than=older_than)
    finally:
        await session.close()

    generate_document = create_generate_document()
    for generation_id, owner_id in requeued:
        await generate_document.execute(generation_id, owner_id)
