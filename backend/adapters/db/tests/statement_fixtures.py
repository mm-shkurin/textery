"""The per-Statements fixtures for the db adapter suite, one line of wiring each.

Split out of `conftest.py`, which had grown past the 200-line limit by holding two
unrelated things: the engine/session lifecycle (which is genuinely conftest work --
it decides what a test session connects to and what gets truncated) and this list,
which is a registry that grows by one entry per Statements class and will keep
growing.

Imported by name into `conftest.py` rather than declared here as a plugin: pytest
registers a fixture when its function object is in the conftest namespace, and
`pytest_plugins` is not permitted in a non-root conftest.

Every fixture here takes `db_session`, which `conftest.py` still owns.
"""

from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from session import create_engine, create_session_factory
from statements.account_storage_statements import AccountStorageStatements
from statements.database_cleanup import truncate_all
from statements.database_url import resolve_test_database_url
from statements.generation_storage_statements import GenerationStorageStatements
from statements.verification_code_storage_statements import VerificationCodeStorageStatements


async def _engine_scoped(build: Callable[..., object]) -> AsyncIterator[object]:
    """Yield `build(session_factory)` against a fresh engine, then clean up.

    Six fixtures below repeated this same env-setup / engine / TRUNCATE / dispose
    block verbatim, which meant a change to the cleanup had six places to land in
    and five places to be forgotten. Cleanup is in a `finally` here, so a failing
    test no longer leaves its rows behind for the next one to trip over.
    """
    resolve_test_database_url()
    engine = create_engine()
    try:
        yield build(create_session_factory(engine))
    finally:
        await truncate_all(engine)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    resolve_test_database_url()
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
def project_feed_statements(db_session: AsyncSession):
    # Named for the storage adapter, not for the feed: `statements` is a top-level
    # package in BOTH this tree and the usecase tests', so two same-named modules
    # under it are one importable name. Whichever tree imported first won, and a
    # whole-suite run handed this fixture the usecase Statements.
    from statements.project_feed_storage_statements import ProjectFeedStorageStatements

    return ProjectFeedStorageStatements(db_session)


@pytest.fixture
def history_paging_statements(db_session: AsyncSession):
    from statements.history_paging_statements import HistoryPagingStatements

    return HistoryPagingStatements(db_session)
