import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

_CODE_DIGITS = 6
_CODE_MODULUS = 10**_CODE_DIGITS
_EXPIRY_MINUTES = 10


class VerificationCode(object):
    """Domain entity for a registration email-verification code."""

    def __init__(self, id: UUID, account_id: UUID, code: str, expires_at: datetime) -> None:
        self.id = id
        self.account_id = account_id
        self.code = code
        self.expires_at = expires_at
        self._consumed_at: Optional[datetime] = None

    @property
    def consumed_at(self) -> Optional[datetime]:
        return self._consumed_at

    @classmethod
    def create(cls, id: UUID, account_id: UUID, code: str, expires_at: datetime) -> "VerificationCode":
        return cls(
            id=id,
            account_id=account_id,
            code=code,
            expires_at=expires_at,
        )

    @classmethod
    def generate(cls, id: UUID, account_id: UUID, created_at: datetime) -> "VerificationCode":
        """Issue a new code: a random 6-digit string expiring 10 minutes from `created_at`."""
        code = f"{secrets.randbelow(_CODE_MODULUS):0{_CODE_DIGITS}d}"
        expires_at = created_at + timedelta(minutes=_EXPIRY_MINUTES)
        return cls.create(
            id=id,
            account_id=account_id,
            code=code,
            expires_at=expires_at,
        )
