"""The one refusal both `/auth/me` usecases raise when the account is gone.

Shared rather than written twice: GetProfile and RenameAccount must be
indistinguishable here. Two copies of the literal are two chances for one route
to grow a message the other does not have, and the whole point of this refusal is
that a caller cannot tell which condition produced it.
"""

from shared.error_codes import ErrorCode
from shared.exceptions import ValidationException

# The same string `security/current_owner.py` answers a missing or forged header
# with, deliberately: a token whose account was deleted and a token that was never
# valid are one outcome, so they must also be one body.
UNAUTHORIZED_MESSAGE = "A valid access token is required."


def unauthorized() -> ValidationException:
    # UNAUTHORIZED is already in the rest layer's _ERROR_CODE_STATUS_MAP as 401,
    # so this needs no new handler and lands in the canonical {error_code, message}
    # envelope like every other refusal.
    return ValidationException(error_code=ErrorCode.UNAUTHORIZED, message=UNAUTHORIZED_MESSAGE)
