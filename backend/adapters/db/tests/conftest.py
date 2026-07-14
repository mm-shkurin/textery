import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_DIR = os.path.dirname(_TESTS_DIR)
_ADAPTERS_DIR = os.path.dirname(_DB_DIR)
_BACKEND_DIR = os.path.dirname(_ADAPTERS_DIR)
_DB_SRC = os.path.join(_DB_DIR, "src")
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")
_USECASE_SRC = os.path.join(_BACKEND_DIR, "usecase", "src")

sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, _DB_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)

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
        await cleanup_connection.execute(text("TRUNCATE TABLE generations"))
        await cleanup_connection.execute(text("TRUNCATE TABLE verification_codes, accounts"))
        await cleanup_connection.commit()
    await engine.dispose()


@pytest.fixture
def generation_storage_statements(db_session: AsyncSession):
    return GenerationStorageStatements(db_session)


@pytest.fixture
def account_storage_statements(db_session: AsyncSession):
    return AccountStorageStatements(db_session)


@pytest.fixture
def verification_code_storage_statements(db_session: AsyncSession):
    return VerificationCodeStorageStatements(db_session)
