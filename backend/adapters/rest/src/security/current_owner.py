from uuid import UUID

from fastapi import Depends, Header

from auth.token_service import TokenService
from shared.exceptions import InvalidTokenException, ValidationException

_BEARER_PREFIX = "bearer "

UNAUTHORIZED_MESSAGE = "A valid access token is required."


def get_token_service() -> TokenService:
    raise NotImplementedError("wired by the application composition root")


def get_current_owner_id(
    authorization: str | None = Header(default=None),
    token_service: TokenService = Depends(get_token_service),
) -> UUID:
    """Resolve the caller's account id from the Authorization header.

    Hand-rolled rather than FastAPI's `HTTPBearer`, for two concrete reasons:
    `HTTPBearer(auto_error=True)` answers **403** on a missing header -- the exact
    status document-ownership-decision.md rules out, because a 403 confirms the
    resource exists -- and it emits `{"detail": ...}` instead of this project's
    `{error_code, message}`. Ten lines here keeps both ours.

    One answer for missing, wrong-scheme, empty, expired, tampered, and
    wrong-type. Distinguishing them tells an attacker which half of the header
    they got right.

    No DB lookup: the signature is the proof, so a round-trip per request buys
    nothing it does not already give. This also uses the TokenService **port**
    directly rather than going through a usecase, which keeps the "usecases must
    not call usecases" rule intact -- rest -> usecase is the allowed direction.
    """
    if not authorization or not authorization.lower().startswith(_BEARER_PREFIX):
        raise _unauthorized()
    token = authorization[len(_BEARER_PREFIX):].strip()
    if not token:
        raise _unauthorized()
    try:
        # read_access_subject, not read_refresh_subject: it enforces type == "access",
        # so a 7-day refresh token cannot be presented here as a document credential.
        return token_service.read_access_subject(token)
    except InvalidTokenException as error:
        raise _unauthorized() from error


def _unauthorized() -> ValidationException:
    # A ValidationException, so it lands in the canonical error shape through the
    # existing handler and its _ERROR_CODE_STATUS_MAP entry -- no new handler.
    return ValidationException(error_code="UNAUTHORIZED", message=UNAUTHORIZED_MESSAGE)
