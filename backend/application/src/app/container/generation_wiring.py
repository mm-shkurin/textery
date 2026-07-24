from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from container.runtime import provider, request_scoped, session_factory, stale_after_minutes
from generation.document_generator import DocumentGenerator
from generation.generate_document import GenerateDocument
from generation.get_generation import GetGeneration
from generation.list_generations import ListGenerations
from generation.request_generation import RequestGeneration
from generation.requeue_stale_generations import RequeueStaleGenerations


class NoOpGenerationQueue:
    """No dedicated job queue — a submitted generation runs inline via FastAPI
    BackgroundTasks. Durability against a worker crash/restart between enqueue
    and execution is provided by the periodic sweep (run_stale_generation_sweep),
    which resets stuck rows to pending and re-triggers execution — not by this
    queue itself.
    """

    async def enqueue(self, generation_id: UUID) -> None:
        pass


@request_scoped
def create_request_generation(session: AsyncSession) -> RequestGeneration:
    return RequestGeneration(
        storage=SqlAlchemyGenerationStorage(session), queue=NoOpGenerationQueue()
    )


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
            usecase = GenerateDocument(storage=storage, provider=provider)
            await usecase.execute(generation_id, owner_id)
        finally:
            await session.close()


def create_generate_document() -> DocumentGenerator:
    return _BackgroundGenerateDocument()


@request_scoped
def create_get_generation(session: AsyncSession) -> GetGeneration:
    return GetGeneration(storage=SqlAlchemyGenerationStorage(session))


@request_scoped
def create_list_generations(session: AsyncSession) -> ListGenerations:
    return ListGenerations(storage=SqlAlchemyGenerationStorage(session))


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
        older_than = datetime.now(UTC) - timedelta(minutes=stale_after_minutes())
        requeued = await usecase.execute(older_than=older_than)
    finally:
        await session.close()

    generate_document = create_generate_document()
    for generation_id, owner_id in requeued:
        await generate_document.execute(generation_id, owner_id)
