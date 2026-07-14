import secrets
from datetime import datetime, timedelta, timezone
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
from shared.exceptions import ValidationException


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class _NullAccountRepository:
    async def save(self, account: Account) -> None:
        return None


class _NullVerificationCodeRepository:
    async def save(self, code) -> None:
        return None


class RegisterUser:
    def __init__(
        self,
        account_repository: Optional[AccountRepository] = None,
        clock: Optional[Clock] = None,
        verification_code_repository: Optional[VerificationCodeRepository] = None,
    ) -> None:
        self.account_repository = account_repository or _NullAccountRepository()
        self.clock = clock or _SystemClock()
        self.verification_code_repository = (
            verification_code_repository or _NullVerificationCodeRepository()
        )

    async def execute(self, email: str, password: str, confirm_password: str) -> RegistrationResult:
        try:
            Email(email)
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
            email=email,
            password_hash=password,
            created_at=created_at,
        )
        await self.account_repository.save(account)

        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = created_at + timedelta(minutes=10)
        verification_code = VerificationCode.create(
            id=uuid4(),
            account_id=account.id,
            code=code,
            expires_at=expires_at,
        )
        await self.verification_code_repository.save(verification_code)

        return RegistrationResult(account=account, verification_code=verification_code)
