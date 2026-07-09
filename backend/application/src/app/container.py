import os
from typing import AsyncIterator
from uuid import UUID

from access.generation.generation_storage import SqlAlchemyGenerationStorage
from generation.generate_document import GenerateDocument
from generation.get_generation import GetGeneration
from generation.request_generation import RequestGeneration
from provider.fake_provider import FakeProvider
from provider.gigachat_provider import GigaChatProvider
from session import create_engine, create_session_factory

GENERATION_PROVIDER_ENV_VAR = "GENERATION_PROVIDER"

_engine = create_engine()
_session_factory = create_session_factory(_engine)


class NoOpGenerationQueue:
    """No queue yet — generation runs inline via FastAPI BackgroundTasks
    instead of a real job queue. Acceptable for the demo; arq worker is
    deferred (known-debt #10/#11). Not a bug.
    """

    async def enqueue(self, generation_id: UUID) -> None:
        pass


async def create_request_generation() -> AsyncIterator[RequestGeneration]:
    session = _session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        yield RequestGeneration(storage=storage, queue=NoOpGenerationQueue())
    finally:
        await session.close()


def _create_provider():
    if os.environ.get(GENERATION_PROVIDER_ENV_VAR, "gigachat") == "fake":
        return FakeProvider()
    return GigaChatProvider()


class _BackgroundGenerateDocument:
    """Dependency-injected into the request scope, but its session is opened
    and closed per `execute()` call — the request's own session is already
    closed by the time BackgroundTasks runs `execute` after the response is
    sent, so it cannot be reused here.
    """

    async def execute(self, generation_id: UUID) -> None:
        session = _session_factory()
        try:
            storage = SqlAlchemyGenerationStorage(session)
            usecase = GenerateDocument(storage=storage, provider=_create_provider())
            await usecase.execute(generation_id)
        finally:
            await session.close()


def create_generate_document() -> GenerateDocument:
    return _BackgroundGenerateDocument()


async def create_get_generation() -> AsyncIterator[GetGeneration]:
    session = _session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        yield GetGeneration(storage=storage)
    finally:
        await session.close()
