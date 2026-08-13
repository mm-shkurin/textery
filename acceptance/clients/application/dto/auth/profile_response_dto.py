from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProfileResponseDto:
    """A `/api/v1/auth/me` response, for both the GET and the PATCH.

    `cache_control` is captured alongside the body because the header is part of
    this route's contract on EVERY response, refusals included -- a DTO that only
    carried the body would make the 401 half of that claim unassertable.
    """

    status_code: int
    body: Optional[dict]
    cache_control: Optional[str]
