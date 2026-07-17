from auth.email import Email
from shared.exceptions import ValidationException

INVALID_EMAIL_ERROR_CODE = "INVALID_EMAIL"
INVALID_EMAIL_MESSAGE = "The email address is not valid."


def validate_email(email: str) -> Email:
    """Parse an email into its value object, or raise the canonical rejection.

    Extracted because RegisterUser and VerifyAccount carried byte-identical
    copies of this -- same error code, same message string. Two copies of one
    rule drift the moment either changes, and here the drift would be worse than
    cosmetic: /verify's answer for a malformed email is what tells a caller the
    address was rejected for its shape rather than for its account state, and
    that distinction only holds while both endpoints agree.

    A plain function, not a shared base class or a usecase: it takes an argument
    and returns a value with no state in between, and the coding rules point
    shared usecase logic at the domain or a stateless helper rather than at a
    usecase that other usecases call.
    """
    try:
        return Email(email)
    except ValueError as error:
        raise ValidationException(
            error_code=INVALID_EMAIL_ERROR_CODE,
            message=INVALID_EMAIL_MESSAGE,
        ) from error
