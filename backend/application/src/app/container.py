import os
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator
from uuid import UUID

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from access.generation.generation_storage import SqlAlchemyGenerationStorage
from auth.login_user import LoginUser
from auth.refresh_access_token import RefreshAccessToken
from auth.register_user import RegisterUser
from auth.verify_account import VerifyAccount
from hashing.bcrypt_password_hasher import BcryptPasswordHasher
from tokens.jwt_token_service import JwtTokenService
from generation.generate_document import GenerateDocument
from generation.get_generation import GetGeneration
from generation.request_generation import RequestGeneration
from generation.requeue_stale_generations import RequeueStaleGenerations
from provider.fake_provider import FakeProvider
from provider.gigachat_provider import GigaChatProvider
from session import SqlAlchemyUnitOfWork, create_engine, create_session_factory
from shared.clock import SystemClock

GENERATION_PROVIDER_ENV_VAR = "GENERATION_PROVIDER"
STALE_AFTER_MINUTES_ENV_VAR = "GENERATION_STALE_AFTER_MINUTES"
DEFAULT_STALE_AFTER_MINUTES = 10
JWT_SECRET_ENV_VAR = "JWT_SECRET"

_engine = create_engine()
_session_factory = create_session_factory(_engine)


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


async def create_register_user() -> AsyncIterator[RegisterUser]:
    session = _session_factory()
    try:
        repository = SqlAlchemyAccountRepository(session)
        verification_code_repository = SqlAlchemyVerificationCodeRepository(session)
        unit_of_work = SqlAlchemyUnitOfWork(session)
        yield RegisterUser(
            password_hasher=BcryptPasswordHasher(),
            account_repository=repository,
            verification_code_repository=verification_code_repository,
            unit_of_work=unit_of_work,
        )
    finally:
        await session.close()


def _create_token_service() -> JwtTokenService:
    # Built once at import, not per request: JwtTokenService refuses an empty
    # secret, so a misconfigured deployment fails at boot with a named error
    # instead of answering 500 on every /login while looking healthy. Same
    # module-level contract `_engine` already follows for DATABASE_URL.
    return JwtTokenService(secret=os.environ.get(JWT_SECRET_ENV_VAR, ""))


_token_service = _create_token_service()


async def create_login_user() -> AsyncIterator[LoginUser]:
    session = _session_factory()
    try:
        repository = SqlAlchemyAccountRepository(session)
        yield LoginUser(
            account_repository=repository,
            password_hasher=BcryptPasswordHasher(),
            token_service=_token_service,
        )
    finally:
        await session.close()


async def create_refresh_access_token() -> AsyncIterator[RefreshAccessToken]:
    session = _session_factory()
    try:
        repository = SqlAlchemyAccountRepository(session)
        yield RefreshAccessToken(
            account_repository=repository,
            token_service=_token_service,
        )
    finally:
        await session.close()


async def create_verify_account() -> AsyncIterator[VerifyAccount]:
    session = _session_factory()
    try:
        repository = SqlAlchemyAccountRepository(session)
        verification_code_repository = SqlAlchemyVerificationCodeRepository(session)
        unit_of_work = SqlAlchemyUnitOfWork(session)
        yield VerifyAccount(
            account_repository=repository,
            verification_code_repository=verification_code_repository,
            clock=SystemClock(),
            unit_of_work=unit_of_work,
        )
    finally:
        await session.close()


def _stale_after_minutes() -> int:
    return int(os.environ.get(STALE_AFTER_MINUTES_ENV_VAR, DEFAULT_STALE_AFTER_MINUTES))


async def run_stale_generation_sweep() -> None:
    """Recovers generations stuck in pending/in_progress after a worker crash
    or restart, since NoOpGenerationQueue is not durable across process
    boundaries. Resets each stale row to pending, then re-triggers execution
    the same way the request path does.
    """
    session = _session_factory()
    try:
        storage = SqlAlchemyGenerationStorage(session)
        usecase = RequeueStaleGenerations(storage=storage)
        older_than = datetime.now(timezone.utc) - timedelta(minutes=_stale_after_minutes())
        requeued_ids = await usecase.execute(older_than=older_than)
    finally:
        await session.close()

    generate_document = create_generate_document()
    for generation_id in requeued_ids:
        await generate_document.execute(generation_id)
