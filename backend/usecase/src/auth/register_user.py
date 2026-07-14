from auth.email import Email
from auth.password import Password
from shared.exceptions import ValidationException


class RegisterUser:
    async def execute(self, email: str, password: str, confirm_password: str) -> None:
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
