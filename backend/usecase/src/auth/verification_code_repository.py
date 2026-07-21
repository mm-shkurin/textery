from datetime import datetime
from typing import Protocol
from uuid import UUID

from auth.verification_code import VerificationCode


class VerificationCodeRepository(Protocol):
    async def save(self, code: VerificationCode) -> None: ...

    async def find_active_by_account_id(self, account_id: UUID) -> VerificationCode | None: ...

    async def transition_to_consumed(self, code_id: UUID, now: datetime) -> bool: ...
