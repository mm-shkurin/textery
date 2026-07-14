from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.email import Email
from auth.password import Password
from shared.clock import Clock
from shared.exceptions import ValidationException


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class _NullAccountRepository:
    async def save(self, account: Account) -> None:
        return None


class RegisterUser:
    def __init__(
        self,
        account_repository: Optional[AccountRepository] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self.account_repository = account_repository or _NullAccountRepository()
        self.clock = clock or _SystemClock()

    async def execute(self, email: str, password: str, confirm_password: str) -> Account:
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
        return account
