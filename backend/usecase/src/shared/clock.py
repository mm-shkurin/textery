from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class SystemClock:
    """Reads the real wall clock. Used when a usecase is constructed without a
    Clock, and by the composition root when wiring one explicitly.
    """

    def now(self) -> datetime:
        return datetime.now(UTC)
