from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from model.auth.oauth_rate_limit_model import OAuthRateLimitModel


class SqlAlchemyRateLimiter:
    """A fixed-window counter shared across instances via Postgres.

    One atomic upsert per hit: the row for the current (bucket, window) is inserted
    at 1 or incremented, and the new count is returned in the same statement — so
    two instances hitting the same bucket cannot both read a stale value and let one
    extra request through. The increment is committed on its own session, decoupled
    from the request's business transaction: the hit must count even when the guarded
    operation later rolls back (the exact case of a throttled or failed request).
    """

    def __init__(
        self, session: AsyncSession, max_requests: int, window_seconds: int
    ) -> None:
        self._session = session
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        window_start = int(now.timestamp()) // self._window_seconds
        statement = (
            pg_insert(OAuthRateLimitModel)
            .values(bucket_key=bucket_key, window_start=window_start, request_count=1)
            .on_conflict_do_update(
                index_elements=["bucket_key", "window_start"],
                set_={"request_count": OAuthRateLimitModel.request_count + 1},
            )
            .returning(OAuthRateLimitModel.request_count)
        )
        count = (await self._session.execute(statement)).scalar_one()
        await self._session.commit()
        return count <= self._max_requests
