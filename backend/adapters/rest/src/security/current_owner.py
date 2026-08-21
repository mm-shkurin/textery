"""Resolving the caller's account id from the `Authorization` header.

Hand-rolled rather than FastAPI's `HTTPBearer`, for two concrete reasons:
`HTTPBearer(auto_error=True)` answers **403** on a missing header -- the exact
status document-ownership-decision.md rules out, because a 403 confirms the
resource exists -- and it emits `{"detail": ...}` instead of this project's
`{error_code, message}`. Ten lines here keeps both ours.

One answer for missing, wrong-scheme, empty, expired, tampered, and wrong-type.
Distinguishing them tells an attacker which half of the header they got right.

**The account is confirmed to exist.** This reverses an earlier decision recorded
here -- "no DB lookup: the signature is the proof" -- and the reason is measured,
not theoretical. A JWT stays valid for its whole lifetime, so a token minted for
an account that has since been deleted (or that belonged to a database this
deployment no longer has) still verifies. Observed on the running stack
2026-08-06: such a token produced `ForeignKeyViolationError on
generations_owner_id_fkey` -> **500** on `POST /api/v1/generations`, while
`documents` -- which carries no foreign key on `owner_id` -- would have accepted
the write and stored rows under an owner that does not exist. One 500 and one
silent corruption from the same cause.

The signature is still the proof of *authenticity*; what it cannot prove is that
the subject is still there. The cost is one primary-key lookup per authenticated
request, which is the cheapest read the database has.

This uses the TokenService and AccountExistence **ports** directly rather than
going through a usecase, which keeps the "usecases must not call usecases" rule
intact -- rest -> usecase is the allowed direction.
"""

from typing import Protocol
from uuid import UUID

from fastapi import Depends, Header

from auth.token_service import TokenService
from shared import error_codes
from shared.exceptions import InvalidTokenException, ValidationException


class AccountExistence(Protocol):
    """Answers whether an account id still names a real account.

    A port of its own rather than the whole `AccountRepository`, because this is
    all the auth boundary is allowed to want: a dependency that could also read
    an email or bump a failed-attempt counter invites a route to do it.
    """

    async def exists(self, account_id: UUID) -> bool: ...


def get_account_existence() -> AccountExistence:
    raise NotImplementedError("wired by the application composition root")


_BEARER_PREFIX = "bearer "

UNAUTHORIZED_MESSAGE = "A valid access token is required."


def get_token_service() -> TokenService:
    raise NotImplementedError("wired by the application composition root")


async def get_current_owner_id(
    authorization: str | None = Header(default=None),
    token_service: TokenService = Depends(get_token_service),
    accounts: AccountExistence = Depends(get_account_existence),
) -> UUID:
    """Resolve the caller's account id, or refuse. See the module docstring."""
    token = _bearer_token(authorization)
    owner_id = _subject_of(token, token_service)
    if not await accounts.exists(owner_id):
        # The same refusal as a bad signature, deliberately: telling the caller
        # that the token was well-formed but the account is gone distinguishes a
        # deleted account from a forged token, and nothing the client can do about
        # either differs.
        raise _unauthorized()
    return owner_id


def _bearer_token(authorization: str | None) -> str:
    """The token half of a well-formed `Authorization: Bearer <token>` header."""
    if not authorization or not authorization.lower().startswith(_BEARER_PREFIX):
        raise _unauthorized()
    token = authorization[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise _unauthorized()
    return token


def _subject_of(token: str, token_service: TokenService) -> UUID:
    """The account id the token asserts.

    read_access_subject, not read_refresh_subject: it enforces type == "access",
    so a 7-day refresh token cannot be presented here as a document credential.
    """
    try:
        return token_service.read_access_subject(token)
    except InvalidTokenException as error:
        raise _unauthorized() from error


def _unauthorized() -> ValidationException:
    # A ValidationException, so it lands in the canonical error shape through the
    # existing handler and its _ERROR_CODE_STATUS_MAP entry -- no new handler.
    return ValidationException(error_code=error_codes.UNAUTHORIZED, message=UNAUTHORIZED_MESSAGE)


async def get_optional_owner_id(
    authorization: str | None = Header(default=None),
    token_service: TokenService = Depends(get_token_service),
    accounts: AccountExistence = Depends(get_account_existence),
) -> UUID | None:
    """The caller's account id, `None` when they presented no token at all.

    For the analytics ingest route, which is the product's only endpoint that
    serves signed-in and anonymous callers through one path. `None` is reserved
    for "no `Authorization` header": a header that IS present and does not
    resolve raises the same refusal as everywhere else, never a downgrade to
    anonymous. A downgrade would detach a signed-in user's events from their
    account every time a token expired -- and it would read in the data as a
    genuine fall in signed-in activity, with nothing to reveal the cause.
    """
    if authorization is None:
        return None
    return await get_current_owner_id(authorization, token_service, accounts)
