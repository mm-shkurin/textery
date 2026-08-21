"""The db-suite fixtures that need an ENGINE rather than one session.

Split out of `statement_fixtures.py`, which had grown past the 200-line limit.
The seam is not arbitrary: every fixture here is engine-scoped because its
Statements class makes a claim about what a DIFFERENT session sees -- a committed
write, a lock, a race -- and one shared session could not express that. The
fixtures left behind in `statement_fixtures.py` all take `db_session` and assert
within one.

Same import contract as its sibling: `conftest.py` star-imports the `__all__`
computed at the bottom, because pytest registers a fixture when its function
object is in the conftest namespace and `pytest_plugins` is not permitted in a
non-root conftest.
"""

from collections.abc import AsyncIterator, Callable

import pytest_asyncio
from fixture_exports import fixture_names

from session import create_engine, create_session_factory
from statements.database_cleanup import truncate_all
from statements.database_url import resolve_test_database_url

_EXPECTED_FIXTURES = 11


async def _engine_scoped(build: Callable[..., object]) -> AsyncIterator[object]:
    """Yield `build(session_factory)` against a fresh engine, then clean up.

    Nine fixtures below repeated this same env-setup / engine / TRUNCATE / dispose
    block verbatim, which meant a change to the cleanup had nine places to land in
    and eight places to be forgotten. Cleanup is in a `finally` here, so a failing
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
async def account_name_storage_statements():
    from statements.account_name_storage_statements import AccountNameStorageStatements

    async for statements in _engine_scoped(AccountNameStorageStatements):
        yield statements


@pytest_asyncio.fixture
async def account_deletion_statements():
    from statements.account_deletion_statements import AccountDeletionStatements

    async for statements in _engine_scoped(AccountDeletionStatements):
        yield statements


@pytest_asyncio.fixture
async def avatar_storage_statements():
    from statements.avatar_storage_statements import AvatarStorageStatements

    async for statements in _engine_scoped(AvatarStorageStatements):
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
async def analytics_storage_statements():
    # Engine-scoped, not session-scoped: the claim is what a DIFFERENT connection
    # sees after the commit. `expire_on_commit=False` means a re-read inside the
    # writing session comes from the identity map, which passes on a row Postgres
    # never received.
    from statements.analytics_event_storage_statements import (
        AnalyticsEventStorageStatements,
    )

    async for statements in _engine_scoped(AnalyticsEventStorageStatements):
        yield statements


@pytest_asyncio.fixture
async def analytics_payload_statements():
    # Engine-scoped for the same reason as its sibling: the claim is what another
    # connection reads back after the commit.
    from statements.analytics_payload_storage_statements import (
        AnalyticsPayloadStorageStatements,
    )

    async for statements in _engine_scoped(AnalyticsPayloadStorageStatements):
        yield statements


@pytest_asyncio.fixture
async def resend_concurrency_statements():
    from statements.resend_concurrency_statements import ResendConcurrencyStatements

    async for statements in _engine_scoped(ResendConcurrencyStatements):
        yield statements


# Computed, never typed out — see fixture_exports for what that is guarding against.
__all__ = fixture_names(globals(), _EXPECTED_FIXTURES)
