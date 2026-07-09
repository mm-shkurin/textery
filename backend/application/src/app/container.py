import os
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
    async def enqueue(self, generation_id: UUID) -> None:
        pass


def create_request_generation() -> RequestGeneration:
    session = _session_factory()
    storage = SqlAlchemyGenerationStorage(session)
    return RequestGeneration(storage=storage, queue=NoOpGenerationQueue())


def _create_provider():
    if os.environ.get(GENERATION_PROVIDER_ENV_VAR, "gigachat") == "fake":
        return FakeProvider()
    return GigaChatProvider()


def create_generate_document() -> GenerateDocument:
    session = _session_factory()
    storage = SqlAlchemyGenerationStorage(session)
    return GenerateDocument(storage=storage, provider=_create_provider())


def create_get_generation() -> GetGeneration:
    session = _session_factory()
    storage = SqlAlchemyGenerationStorage(session)
    return GetGeneration(storage=storage)
