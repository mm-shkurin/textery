import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.exceptions import ConfigurationException

DATABASE_URL_ENV_VAR = "DATABASE_URL"


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
    return create_async_engine(to_async_database_url(database_url))


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
