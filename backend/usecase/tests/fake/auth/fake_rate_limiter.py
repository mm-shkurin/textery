from datetime import datetime


class FakeRateLimiter:
    """An in-memory fixed-window counter with the storage adapter's semantics.

    Counts per (bucket, window) and answers False from the hit that exceeds the
    allowance onward, exactly as the Postgres upsert does -- so a test that pins
    "the N+1st attempt is refused" pins the same boundary production runs.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self.counts: dict[tuple[str, int], int] = {}

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        window = int(now.timestamp()) // self._window_seconds
        key = (bucket_key, window)
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= self._max_requests
