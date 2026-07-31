import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.exceptions import ConfigurationException

DATABASE_URL_ENV_VAR = "DATABASE_URL"

# 30 minutes. Comfortably under the idle timeouts a managed Postgres or a
# connection proxy typically imposes, and long enough that recycling is not itself
# a source of churn.
RECYCLE_CONNECTIONS_AFTER_SECONDS = 1800


def to_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def create_engine() -> AsyncEngine:
    # container/runtime builds the engine at module level, so this runs at import
    # and its message is the whole diagnosis a misconfigured deployment gets.
    # Unchecked, an unset URL surfaces as an AttributeError on None that names
    # neither the variable nor configuration as the problem. Same contract
    # JwtTokenService applies to JWT_SECRET.
    database_url = os.environ.get(DATABASE_URL_ENV_VAR)
    if not database_url:
        raise ConfigurationException(
            f"{DATABASE_URL_ENV_VAR} is not set. Expected a PostgreSQL connection string, "
            "e.g. postgresql+asyncpg://user:password@host:5432/db"
        )
    return create_async_engine(
        to_async_database_url(database_url),
        # Without this, a connection the pool believes is open but Postgres has
        # already closed -- an idle timeout, a database restart, a failover -- is
        # discovered by the query that runs on it. The user-visible symptom is a
        # 500 on the first request after every quiet period, one per stale
        # connection, and it clears up by itself, which is what makes it hard to
        # catch. pool_pre_ping spends a round-trip proving the connection is alive
        # and transparently replaces it if not.
        pool_pre_ping=True,
        # SQLAlchemy's default pool never returns a connection to Postgres, so a
        # connection that has been idle for hours is kept and re-offered. Recycling
        # below every reasonable server-side idle timeout means the pool retires
        # them before the server does, and pre_ping has far less to repair.
        pool_recycle=RECYCLE_CONNECTIONS_AFTER_SECONDS,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
