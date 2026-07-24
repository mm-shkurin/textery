import os
import socket
from collections.abc import AsyncIterator, Callable
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from session import create_engine, create_session_factory
from statements.account_storage_statements import AccountStorageStatements
from statements.database_cleanup import truncate_all
from statements.generation_storage_statements import GenerationStorageStatements
from statements.verification_code_storage_statements import VerificationCodeStorageStatements

TEST_DATABASE_URL_ENV_VAR = "TEST_DATABASE_URL"
DEFAULT_TEST_DATABASE_URL = "postgresql://textery:change-me@localhost:5432/textery"
# Short on purpose: this is a liveness probe, not the connection itself. The
# answer is "is anything listening", and anything listening answers instantly.
_PROBE_TIMEOUT_SECONDS = 3


def _test_database_url() -> str:
    """Point the adapter's own `create_engine()` at the test database."""
    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    os.environ["DATABASE_URL"] = os.environ[TEST_DATABASE_URL_ENV_VAR]
    return os.environ[TEST_DATABASE_URL_ENV_VAR]


@pytest.fixture(scope="session", autouse=True)
def require_database() -> None:
    """Skip this whole suite with a named reason when there is no database.

    Without it, `pytest` on a machine with no Postgres does not fail -- it
    *hangs*, because every fixture here opens a connection and waits out the
    driver's own timeout, once per test. A contributor running the documented
    `pytest` command sees no output and no reason, which reads as a broken
    checkout rather than a missing service. CI provides Postgres, so this probe
    passes there and gates nothing.
    """
    parts = urlsplit(_test_database_url())
    host, port = parts.hostname or "localhost", parts.port or 5432
    try:
        with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT_SECONDS):
            return
    except OSError as error:
        pytest.skip(
            f"no database listening at {host}:{port} ({error}). These are the adapter's "
            f"integration tests and need a real Postgres: set {TEST_DATABASE_URL_ENV_VAR}, "
            f"or run `pytest domain usecase` for the layers that need no database.",
            allow_module_level=True,
        )


async def _engine_scoped(build: Callable[..., object]) -> AsyncIterator[object]:
    """Yield `build(session_factory)` against a fresh engine, then clean up.

    Six fixtures below repeated this same env-setup / engine / TRUNCATE / dispose
    block verbatim, which meant a change to the cleanup had six places to land in
    and five places to be forgotten. Cleanup is in a `finally` here, so a failing
    test no longer leaves its rows behind for the next one to trip over.
    """
    _test_database_url()
    engine = create_engine()
    try:
        yield build(create_session_factory(engine))
    finally:
        await truncate_all(engine)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    _test_database_url()
    engine = create_engine()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            yield session
            await session.rollback()
    finally:
        await truncate_all(engine)
        await engine.dispose()


@pytest.fixture
def generation_storage_statements(db_session: AsyncSession):
    return GenerationStorageStatements(db_session)


@pytest.fixture
def account_storage_statements(db_session: AsyncSession):
    return AccountStorageStatements(db_session)


@pytest_asyncio.fixture
async def account_concurrency_statements():
    from statements.account_concurrency_statements import AccountConcurrencyStatements

    async for statements in _engine_scoped(AccountConcurrencyStatements):
        yield statements


@pytest_asyncio.fixture
async def failed_attempt_concurrency_statements():
    from statements.failed_attempt_concurrency_statements import (
        FailedAttemptConcurrencyStatements,
    )

    async for statements in _engine_scoped(FailedAttemptConcurrencyStatements):
        yield statements


@pytest_asyncio.fixture
async def account_to_domain_roundtrip_statements():
    from statements.account_to_domain_roundtrip_statements import (
        AccountToDomainRoundtripStatements,
    )

    async for statements in _engine_scoped(AccountToDomainRoundtripStatements):
        yield statements


@pytest_asyncio.fixture
async def reset_failed_attempts_statements():
    from statements.reset_failed_attempts_statements import (
        ResetFailedAttemptsStatements,
    )

    async for statements in _engine_scoped(ResetFailedAttemptsStatements):
        yield statements


@pytest_asyncio.fixture
async def verification_code_concurrency_statements():
    from statements.verification_code_concurrency_statements import (
        VerificationCodeConcurrencyStatements,
    )

    async for statements in _engine_scoped(VerificationCodeConcurrencyStatements):
        yield statements


@pytest_asyncio.fixture
async def resend_concurrency_statements():
    from statements.resend_concurrency_statements import ResendConcurrencyStatements

    async for statements in _engine_scoped(ResendConcurrencyStatements):
        yield statements


@pytest.fixture
def resend_ordering_statements(db_session: AsyncSession):
    from statements.resend_ordering_statements import ResendOrderingStatements

    return ResendOrderingStatements(db_session)


@pytest.fixture
def verification_code_storage_statements(db_session: AsyncSession):
    return VerificationCodeStorageStatements(db_session)


@pytest.fixture
def sql_alchemy_unit_of_work_statements(db_session: AsyncSession):
    from statements.sql_alchemy_unit_of_work_statements import SqlAlchemyUnitOfWorkStatements

    return SqlAlchemyUnitOfWorkStatements(db_session)


@pytest.fixture
def document_storage_statements(db_session: AsyncSession):
    from statements.document_storage_statements import DocumentStorageStatements

    return DocumentStorageStatements(db_session)


@pytest.fixture
def history_paging_statements(db_session: AsyncSession):
    from statements.history_paging_statements import HistoryPagingStatements

    return HistoryPagingStatements(db_session)
