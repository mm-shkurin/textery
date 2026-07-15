from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.email import Email
from auth.password import Password
from auth.registration_result import RegistrationResult
from auth.verification_code import VerificationCode
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock
from shared.exceptions import ConflictException, RegistrationFailedException, ValidationException
from shared.unit_of_work import UnitOfWork


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class _NullRepository:
    async def save(self, entity) -> None:
        return None


class _NullUnitOfWork:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class RegisterUser:
    REGISTRATION_FAILED_MESSAGE = (
        "Registration could not be completed due to an unexpected error. Please try again."
    )

    def __init__(
        self,
        account_repository: Optional[AccountRepository] = None,
        clock: Optional[Clock] = None,
        verification_code_repository: Optional[VerificationCodeRepository] = None,
        unit_of_work: Optional[UnitOfWork] = None,
    ) -> None:
        self.account_repository = account_repository or _NullRepository()
        self.clock = clock or _SystemClock()
        self.verification_code_repository = (
            verification_code_repository or _NullRepository()
        )
        self.unit_of_work = unit_of_work or _NullUnitOfWork()

    async def execute(self, email: str, password: str, confirm_password: str) -> RegistrationResult:
        try:
            email_value_object = Email(email)
        except ValueError:
            raise ValidationException(
                error_code="INVALID_EMAIL",
                message="The email address is not valid.",
            )
        try:
            Password(password)
        except ValueError:
            raise ValidationException(
                error_code="INVALID_PASSWORD",
                message="The password does not meet the password policy.",
            )
        if password != confirm_password:
            raise ValidationException(
                error_code="PASSWORD_MISMATCH",
                message="The password confirmation does not match.",
            )
        created_at = self.clock.now()
        account = Account.create(
            id=uuid4(),
            email=email_value_object.value,
            password_hash=password,
            created_at=created_at,
        )
        try:
            await self.account_repository.save(account)
        except ConflictException:
            raise ValidationException(
                error_code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email address already exists.",
            )

        verification_code = VerificationCode.generate(
            id=uuid4(),
            account_id=account.id,
            created_at=created_at,
        )
        try:
            await self.verification_code_repository.save(verification_code)
            await self.unit_of_work.commit()
        except Exception:
            try:
                await self.unit_of_work.rollback()
            except Exception:
                pass
            raise RegistrationFailedException(message=self.REGISTRATION_FAILED_MESSAGE)

        return RegistrationResult(account=account, verification_code=verification_code)
