import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from session import create_engine, create_session_factory
from statements.account_storage_statements import AccountStorageStatements
from statements.generation_storage_statements import GenerationStorageStatements
from statements.verification_code_storage_statements import VerificationCodeStorageStatements

TEST_DATABASE_URL_ENV_VAR = "TEST_DATABASE_URL"
DEFAULT_TEST_DATABASE_URL = "postgresql://textery:change-me@localhost:5432/textery"


@pytest_asyncio.fixture
async def db_session():
    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    os.environ["DATABASE_URL"] = os.environ[TEST_DATABASE_URL_ENV_VAR]
    engine = create_engine()
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session
        await session.rollback()
    async with engine.connect() as cleanup_connection:
        # One statement: documents.owner_id and generations.owner_id both reference
        # accounts.id, so truncating accounts on its own fails with "cannot truncate
        # a table referenced in a foreign key constraint". Postgres only allows it
        # when every referencing table is truncated in the same command -- which is
        # why generations moved in here rather than staying a separate TRUNCATE.
        await cleanup_connection.execute(
            text("TRUNCATE TABLE generations, documents, verification_codes, accounts")
        )
        await cleanup_connection.commit()
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

    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    os.environ["DATABASE_URL"] = os.environ[TEST_DATABASE_URL_ENV_VAR]
    engine = create_engine()
    session_factory = create_session_factory(engine)
    yield AccountConcurrencyStatements(session_factory)
    async with engine.connect() as cleanup_connection:
        await cleanup_connection.execute(
            text("TRUNCATE TABLE generations, documents, verification_codes, accounts")
        )
        await cleanup_connection.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def verification_code_concurrency_statements():
    from statements.verification_code_concurrency_statements import (
        VerificationCodeConcurrencyStatements,
    )

    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    os.environ["DATABASE_URL"] = os.environ[TEST_DATABASE_URL_ENV_VAR]
    engine = create_engine()
    session_factory = create_session_factory(engine)
    yield VerificationCodeConcurrencyStatements(session_factory)
    async with engine.connect() as cleanup_connection:
        await cleanup_connection.execute(
            text("TRUNCATE TABLE generations, documents, verification_codes, accounts")
        )
        await cleanup_connection.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def resend_concurrency_statements():
    from statements.resend_concurrency_statements import ResendConcurrencyStatements

    os.environ.setdefault(TEST_DATABASE_URL_ENV_VAR, DEFAULT_TEST_DATABASE_URL)
    os.environ["DATABASE_URL"] = os.environ[TEST_DATABASE_URL_ENV_VAR]
    engine = create_engine()
    session_factory = create_session_factory(engine)
    yield ResendConcurrencyStatements(session_factory)
    async with engine.connect() as cleanup_connection:
        await cleanup_connection.execute(
            text("TRUNCATE TABLE generations, documents, verification_codes, accounts")
        )
        await cleanup_connection.commit()
    await engine.dispose()


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
