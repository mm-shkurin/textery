import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine

# The layer roots come from `prepend_sys_path` in alembic.ini, so these are
# ordinary top-level imports. The model imports are unused by name and kept for
# their side effect: each registers its table on Base.metadata, which is what
# autogenerate diffs against. Drop one and Alembic proposes dropping its table.
from model.auth.account_model import AccountModel  # noqa: F401
from model.auth.verification_code_model import VerificationCodeModel  # noqa: F401
from model.base import Base
from model.document.document_model import DocumentModel  # noqa: F401
from model.generation.generation_model import GenerationModel  # noqa: F401
from session import create_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    database_url = os.environ.get("DATABASE_URL")
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine: AsyncEngine = create_engine()
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
