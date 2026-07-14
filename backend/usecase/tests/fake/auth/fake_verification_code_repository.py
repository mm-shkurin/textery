from auth.verification_code import VerificationCode


class FakeVerificationCodeRepository:
    def __init__(self) -> None:
        self.saved_codes: list[VerificationCode] = []

    async def save(self, code: VerificationCode) -> None:
        self.saved_codes.append(code)
