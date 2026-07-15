from typing import Optional
from uuid import UUID

from auth.verification_code import VerificationCode


class FakeVerificationCodeRepository:
    def __init__(self) -> None:
        self.saved_codes: list[VerificationCode] = []
        self.raise_on_save: Optional[Exception] = None

    async def save(self, code: VerificationCode) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_codes.append(code)

    async def find_active_by_account_id(self, account_id: UUID) -> Optional[VerificationCode]:
        for code in reversed(self.saved_codes):
            if code.account_id == account_id and code.consumed_at is None:
                return code
        return None
