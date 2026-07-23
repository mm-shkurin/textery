from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base


class OAuthRateLimitModel(Base):
    """A fixed-window request counter, one row per (bucket, window).

    `window_start` is the epoch second floored to the window size, so all hits in
    one window share a row and the count is incremented atomically with an upsert.
    Rows for elapsed windows are simply never read again; they carry no secret, so
    a periodic sweep can drop them without affecting correctness.
    """

    __tablename__ = "oauth_rate_limits"

    bucket_key: Mapped[str] = mapped_column(String, primary_key=True)
    window_start: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
