from datetime import datetime

MAX_REQUESTS = 3
WINDOW_SECONDS = 60
RATE_LIMITED_BODY = {
    "error_code": "AUTH_RATE_LIMITED",
    "message": "Too many attempts from this source. Please try again later.",
}


class CountingRateLimiter:
    """The storage port's semantics in memory: refuses from the hit that exceeds."""

    def __init__(self, max_requests: int = MAX_REQUESTS) -> None:
        self._max_requests = max_requests
        self._counts: dict[tuple[str, int], int] = {}

    async def register_hit(self, bucket_key: str, now: datetime) -> bool:
        key = (bucket_key, int(now.timestamp()) // WINDOW_SECONDS)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key] <= self._max_requests


def credentials_for(attempt: int) -> dict[str, str]:
    """A DIFFERENT account per attempt -- the whole point of the scenario.

    The per-account lockout would already refuse the same address N times over.
    Spreading the attempts across N+1 addresses is exactly the shape it cannot
    see, so only a bound keyed on the source can refuse the last one.
    """
    return {"email": f"victim{attempt}@example.com", "password": "Passw0rd1!"}
