from typing import Optional

from auth.register_user import RegisterUser
from scope.register_request_scope import RegisterRequestScope
from shared.exceptions import ValidationException


class RegisterStatements:
    EXPECTED_INVALID_EMAIL_ERROR_CODE = "INVALID_EMAIL"
    EXPECTED_INVALID_EMAIL_MESSAGE = "The email address is not valid."

    def __init__(self) -> None:
        self.thrown_exception: Optional[Exception] = None

    async def attempt_registering_with_email(self, email: Optional[str]) -> None:
        scope = RegisterRequestScope.builder(email=email)
        await self._attempt_registering(scope)

    async def _attempt_registering(self, scope: RegisterRequestScope) -> None:
        usecase = RegisterUser()
        try:
            await usecase.execute(
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
