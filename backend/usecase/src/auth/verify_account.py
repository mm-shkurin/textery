from typing import Optional

from auth.account_repository import AccountRepository
from auth.email import Email
from auth.verification_code_repository import VerificationCodeRepository
from auth.verification_code_value import VerificationCodeValue
from shared.clock import Clock
from shared.exceptions import ValidationException, VerificationFailedException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class VerifyAccount:
    VERIFICATION_FAILED_MESSAGE = (
        "Verification could not be completed due to an unexpected error. Please try again."
    )

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
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, email: str, code: str) -> None:
        # Both shape checks run before any repository lookup, so a malformed
        # request costs zero queries. Email is validated first: a request bad on
        # both axes answers INVALID_EMAIL, matching RegisterUser's order.
        normalized_email = self._validate_email(email).value
        self._validate_code(code)
        account = await self.account_repository.find_by_email(normalized_email)
        verification_code = await self.verification_code_repository.find_active_by_account_id(account.id)

        if verification_code.matches(code):
            account.verify()
            verification_code.consume(consumed_at=self.clock.now())
            try:
                await self.account_repository.save(account)
                await self.verification_code_repository.save(verification_code)
                await self.unit_of_work.commit()
            except Exception:
                await self._rollback_silently()
                raise VerificationFailedException(message=self.VERIFICATION_FAILED_MESSAGE)

    def _validate_email(self, email: str) -> Email:
        try:
            return Email(email)
        except ValueError:
            raise ValidationException(
                error_code="INVALID_EMAIL",
                message="The email address is not valid.",
            )

    def _validate_code(self, code: str) -> VerificationCodeValue:
        try:
            return VerificationCodeValue(code)
        except ValueError:
            raise ValidationException(
                error_code="INVALID_CODE",
                message="The verification code is not valid.",
            )

    async def _rollback_silently(self) -> None:
        try:
            await self.unit_of_work.rollback()
        except Exception:
            pass
