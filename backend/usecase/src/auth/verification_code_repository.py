from typing import Protocol

from auth.verification_code import VerificationCode


class VerificationCodeRepository(Protocol):
    async def save(self, code: VerificationCode) -> None:
        ...
