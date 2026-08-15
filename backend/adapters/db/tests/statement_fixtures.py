"""The db-suite fixtures that share ONE session, plus the session itself.

Split out of `conftest.py`, which had grown past the 200-line limit by holding two
unrelated things: the engine/session lifecycle (which is genuinely conftest work --
it decides what a test session connects to and what gets truncated) and this list,
which is a registry that grows by one entry per Statements class and will keep
growing.

It then grew past the limit itself, and the engine-scoped half moved to
`engine_scoped_fixtures.py`. The seam is what each fixture needs: everything here
takes `db_session` and asserts within one session; a Statements class whose claim
is about what a DIFFERENT session sees belongs in the sibling module.

Imported into `conftest.py` rather than declared here as a plugin: pytest registers
a fixture when its function object is in the conftest namespace, and
`pytest_plugins` is not permitted in a non-root conftest. That import is a star
import over the `__all__` computed at the bottom of this file, and that is the
point -- see the note there.
"""

import pytest
import pytest_asyncio
from fixture_exports import fixture_names
from sqlalchemy.ext.asyncio import AsyncSession

from session import create_engine, create_session_factory
from statements.account_storage_statements import AccountStorageStatements
from statements.database_cleanup import truncate_all
from statements.database_url import resolve_test_database_url
from statements.generation_storage_statements import GenerationStorageStatements
from statements.verification_code_storage_statements import VerificationCodeStorageStatements

_EXPECTED_FIXTURES = 9


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


# Computed, never typed out — see fixture_exports for what that is guarding against.
__all__ = fixture_names(globals(), _EXPECTED_FIXTURES)
