from typing import Optional

from auth.account_repository import AccountRepository
from auth.email import Email
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock
from shared.unit_of_work import UnitOfWork


class _NullUnitOfWork:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class VerifyAccount:
    def __init__(
        self,
        account_repository: AccountRepository,
        verification_code_repository: VerificationCodeRepository,
        clock: Clock,
        unit_of_work: Optional[UnitOfWork] = None,
    ) -> None:
        self.account_repository = account_repository
        self.verification_code_repository = verification_code_repository
        self.clock = clock
        self.unit_of_work = unit_of_work or _NullUnitOfWork()

    async def execute(self, email: str, code: str) -> None:
        normalized_email = Email(email).value
        account = await self.account_repository.find_by_email(normalized_email)
        verification_code = await self.verification_code_repository.find_active_by_account_id(account.id)

        if verification_code.code == code:
            account.verify()
            verification_code.consume(consumed_at=self.clock.now())
            await self.account_repository.save(account)
            await self.verification_code_repository.save(verification_code)
            await self.unit_of_work.commit()
