from auth.account_repository import AccountRepository
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock


class VerifyAccount:
    def __init__(
        self,
        account_repository: AccountRepository,
        verification_code_repository: VerificationCodeRepository,
        clock: Clock,
    ) -> None:
        self.account_repository = account_repository
        self.verification_code_repository = verification_code_repository
        self.clock = clock

    async def execute(self, email: str, code: str) -> None:
        raise NotImplementedError()
