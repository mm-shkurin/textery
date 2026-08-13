from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AvatarResponseDto:
    """A `GET /api/v1/auth/me/avatar` response.

    Carries `content` (the raw image bytes) AND `body` (the parsed JSON of an
    error), because this route answers with one or the other and a test asserting
    a 404 needs the envelope while a test asserting a 200 needs the bytes.

    The three headers are fields rather than a dict: they are the security half of
    this route's contract, and naming them here means a test cannot assert the
    status while silently ignoring whether `nosniff` was sent.
    """

    status_code: int
    content: bytes
    body: Optional[dict]
    content_type: Optional[str]
    cache_control: Optional[str]
    x_content_type_options: Optional[str]
