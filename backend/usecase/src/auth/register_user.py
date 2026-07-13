from auth.email import Email
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
