"""Whether a caller has proven they mean to delete their own account.

Its own module because this is the entire security value of the endpoint. What
follows it is an irreversible DELETE; if this returns True wrongly, nothing
downstream can catch the mistake and nothing can undo it.
"""

import unicodedata

from auth.account import Account
from auth.email import Email
from auth.password_hasher import PasswordHasher
from shared.exceptions import ValidationException

DELETION_CONFIRMATION_INVALID_CODE = "DELETION_CONFIRMATION_INVALID"
DELETION_CONFIRMATION_INVALID_MESSAGE = "The confirmation does not match. Nothing was deleted."


def confirmation_invalid() -> ValidationException:
    """One refusal for a wrong password AND for a mismatched address.

    Deliberately NOT a 401: the session is perfectly valid and the caller is who
    they say they are. What failed is the confirmation, and answering 401 would
    tell a client whose token is fine to go and renew it -- and, in the frontend's
    interceptor, potentially to end a healthy session.

    One code for both causes because the caller already knows which form they
    sent; splitting it would only describe their own request back to them.
    """
    return ValidationException(
        error_code=DELETION_CONFIRMATION_INVALID_CODE,
        message=DELETION_CONFIRMATION_INVALID_MESSAGE,
    )


def has_password(account: Account) -> bool:
    """True when this account can be confirmed by password.

    OAuth-only accounts are created with `password_hash=""`
    (complete_oauth_callback.py), so there is no password that could ever verify
    against them -- which is why the branch below is chosen by what the ACCOUNT
    has, never by which field the client happened to send.
    """
    return account.password_hash != ""


def password_confirms(account: Account, password: object, password_hasher: PasswordHasher) -> bool:
    """The submitted password verifies against this account's stored hash.

    THE EMPTY PASSWORD NEVER CONFIRMS. An OAuth account stores `""` as its hash,
    and a check written as "does the submitted value match the stored one" would
    delete such an account for a body of `{"password": ""}`. The guard is not the
    hasher's job: bcrypt would refuse a `""` hash, but relying on that puts the
    single most destructive path in the product at the mercy of a library's
    error-handling detail. Refused here, explicitly, before the hasher is reached.

    A non-string is refused rather than coerced: the request DTO types the field
    permissively so the value arrives here instead of triggering a Pydantic 422
    that echoes the rejected input back.
    """
    if not has_password(account):
        return False
    if not isinstance(password, str) or password == "":
        return False
    # NFC only, exactly as LoginUser does it -- the hash was computed from the NFC
    # form, so a decomposed submission of the same password would not verify.
    # Deliberately NOT Password(...).value: that also enforces the current policy,
    # and a credential predating a policy change must still be usable by its owner.
    return password_hasher.verify(unicodedata.normalize("NFC", password), account.password_hash)


def email_confirms(account: Account, confirm_email: object) -> bool:
    """The submitted address is this account's own, compared canonically.

    Only ever consulted for an account with NO password. On an account that has
    one, accepting an address instead would reduce the gate to knowing an email
    the user is looking at on screen -- the deletion screen shows it.

    Normalised through `Email` so the comparison happens in the same canonical
    form the address was stored in (trimmed, NFC, case-folded). A malformed value
    cannot match any stored account, so it is a plain mismatch, not a separate
    INVALID_EMAIL: this endpoint has exactly one refusal.
    """
    if has_password(account):
        return False
    if not isinstance(confirm_email, str):
        return False
    try:
        submitted = Email(confirm_email.strip()).value
    except ValueError:
        return False
    return submitted == account.email
