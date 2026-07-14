from typing import Optional

from auth.register_user import RegisterUser
from scope.register_request_scope import RegisterRequestScope
from shared.exceptions import ValidationException


class RegisterStatements:
    EXPECTED_INVALID_EMAIL_ERROR_CODE = "INVALID_EMAIL"
    EXPECTED_INVALID_EMAIL_MESSAGE = "The email address is not valid."
    EXPECTED_INVALID_PASSWORD_ERROR_CODE = "INVALID_PASSWORD"
    EXPECTED_INVALID_PASSWORD_MESSAGE = "The password does not meet the password policy."

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None

    async def attempt_registering_with_email(self, email: Optional[str]) -> None:
        await self._attempt_registering(RegisterRequestScope.builder(email=email))

    async def attempt_registering_with_password(self, password: Optional[str]) -> None:
        await self._attempt_registering(
            RegisterRequestScope.builder(password=password, confirm_password=password)
        )

    async def _attempt_registering(self, scope: RegisterRequestScope) -> None:
        try:
            await RegisterUser().execute(
                email=scope.email,
                password=scope.password,
                confirm_password=scope.confirm_password,
            )
        except Exception as exc:
            self.thrown_exception = exc

    def assert_invalid_email_error_raised(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}"
        )
        assert self.thrown_exception.error_code == self.EXPECTED_INVALID_EMAIL_ERROR_CODE, (
            f"expected error_code '{self.EXPECTED_INVALID_EMAIL_ERROR_CODE}', "
            f"got '{self.thrown_exception.error_code}'"
        )
        assert self.thrown_exception.message == self.EXPECTED_INVALID_EMAIL_MESSAGE, (
            f"expected message '{self.EXPECTED_INVALID_EMAIL_MESSAGE}', "
            f"got '{self.thrown_exception.message}'"
        )

    def assert_invalid_password_error_raised(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected ValidationException to be raised, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else 'no exception'}"
        )
        assert self.thrown_exception.error_code == self.EXPECTED_INVALID_PASSWORD_ERROR_CODE, (
            f"expected error_code '{self.EXPECTED_INVALID_PASSWORD_ERROR_CODE}', "
            f"got '{self.thrown_exception.error_code}'"
        )
        assert self.thrown_exception.message == self.EXPECTED_INVALID_PASSWORD_MESSAGE, (
            f"expected message '{self.EXPECTED_INVALID_PASSWORD_MESSAGE}', "
            f"got '{self.thrown_exception.message}'"
        )
