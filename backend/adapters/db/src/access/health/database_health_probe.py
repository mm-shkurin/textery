from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseHealthProbe:
    """HealthProbe implementation: round-trip the smallest possible statement.

    `SELECT 1` rather than reading a table. It proves the pool handed out a live
    connection and Postgres answered on it, which is exactly the claim the probe
    makes -- and it stays true through every migration, whereas a probe that reads
    an application table would start failing the day that table is renamed and
    report an outage that is really a refactor.

    Takes the same request-scoped `AsyncSession` every other storage adapter takes,
    so the check exercises the real pool rather than a private connection that
    could be healthy while the pool the traffic uses is not.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> None:
        await self._session.execute(text("SELECT 1"))
