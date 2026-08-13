from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeletionResponseDto:
    """A `POST /api/v1/auth/me/deletion` response.

    `body` is None on success: the endpoint answers 204 with no content, because
    there is no resource left to describe. It carries the canonical
    `{error_code, message}` envelope on a refusal.
    """

    status_code: int
    body: Optional[dict]
