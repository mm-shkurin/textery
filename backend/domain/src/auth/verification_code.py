from datetime import datetime
from uuid import UUID


class VerificationCode(object):
    """Domain entity for a registration email-verification code."""

    def __init__(self, id: UUID, account_id: UUID, code: str, expires_at: datetime) -> None:
        self.id = id
        self.account_id = account_id
        self.code = code
        self.expires_at = expires_at

    @classmethod
    def create(cls, id: UUID, account_id: UUID, code: str, expires_at: datetime) -> "VerificationCode":
        return cls(
            id=id,
            account_id=account_id,
            code=code,
            expires_at=expires_at,
        )
