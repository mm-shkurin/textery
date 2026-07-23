import secrets
from datetime import datetime, timedelta
from uuid import UUID

HANDOFF_CODE_BYTES = 32
MAX_HANDOFF_CODE_LENGTH = 512


class HandoffCode:
    """The opaque, single-use, short-TTL code that rides in the callback redirect.

    It exists so the JWTs never have to: a URL lands in browser history, in the
    Referer header of the next request, and in every proxy access log on the way.
    An opaque code that dies on first redemption is survivable there; a token is not.
    """

    def __init__(
        self,
        value: str,
        account_id: UUID,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        self.value = value
        self.account_id = account_id
        self.created_at = created_at
        self.expires_at = expires_at

    @classmethod
    def generate(cls, account_id: UUID, created_at: datetime, ttl_seconds: int) -> "HandoffCode":
        return cls(
            value=secrets.token_urlsafe(HANDOFF_CODE_BYTES),
            account_id=account_id,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=ttl_seconds),
        )

    def is_expired_at(self, moment: datetime) -> bool:
        # `>=` not `>`: the TTL boundary itself is already expired, so a code can
        # never be redeemed at the exact instant it lapses.
        return moment >= self.expires_at
