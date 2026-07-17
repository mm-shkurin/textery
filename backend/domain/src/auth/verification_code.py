import secrets
from datetime import datetime, timedelta
from uuid import UUID

from auth.verification_code_value import VerificationCodeValue

_EXPIRY_MINUTES = 10


class VerificationCode:
    """Domain entity for a registration email-verification code."""

    def __init__(
        self,
        id: UUID,
        account_id: UUID,
        code: str,
        expires_at: datetime,
        consumed_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.account_id = account_id
        self._code = code
        self.expires_at = expires_at
        self._consumed_at = consumed_at

    @property
    def code(self) -> str:
        return self._code

    @property
    def consumed_at(self) -> datetime | None:
        return self._consumed_at

    def matches(self, code: str) -> bool:
        # compare_digest, not ==: `==` on str short-circuits at the first differing
        # character, so the time it takes to answer leaks how many leading digits
        # were right. That turns a 10**6 code space into ~10*6 guesses for a
        # caller who can measure. The code is a secret with a 10-minute life, and
        # VerifyAccount is deliberately careful elsewhere about not answering
        # differently for different failures -- a timing oracle would undo that.
        return secrets.compare_digest(self._code, code)

    def consume(self, consumed_at: datetime) -> None:
        self._consumed_at = consumed_at

    @classmethod
    def create(cls, id: UUID, account_id: UUID, code: str, expires_at: datetime) -> "VerificationCode":
        return cls(
            id=id,
            account_id=account_id,
            code=code,
            expires_at=expires_at,
        )

    @classmethod
    def reconstitute(
        cls,
        id: UUID,
        account_id: UUID,
        code: str,
        expires_at: datetime,
        consumed_at: datetime | None,
    ) -> "VerificationCode":
        """Rebuild a VerificationCode from storage, preserving consumed_at."""
        return cls(
            id=id,
            account_id=account_id,
            code=code,
            expires_at=expires_at,
            consumed_at=consumed_at,
        )

    @classmethod
    def generate(cls, id: UUID, account_id: UUID, created_at: datetime) -> "VerificationCode":
        """Issue a new code: a random 6-digit string expiring 10 minutes from `created_at`.

        The draw is bounded by the full code space (10 ** DIGIT_COUNT), *not* by
        DIGIT_COUNT itself -- the latter would silently collapse entropy to six
        possible codes while still producing a well-shaped, zero-padded string.

        `.value` is stored, never the value object: `matches()` compares against a
        submitted `str`, so storing the object would fail every correct code.
        """
        digits = VerificationCodeValue.DIGIT_COUNT
        code = VerificationCodeValue(f"{secrets.randbelow(10**digits):0{digits}d}").value
        expires_at = created_at + timedelta(minutes=_EXPIRY_MINUTES)
        return cls.create(
            id=id,
            account_id=account_id,
            code=code,
            expires_at=expires_at,
        )
