from typing import Optional

from auth.verification_code import VerificationCode


class FakeVerificationCodeRepository:
    def __init__(self) -> None:
        self.saved_codes: list[VerificationCode] = []
        self.raise_on_save: Optional[Exception] = None

    async def save(self, code: VerificationCode) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_codes.append(code)
