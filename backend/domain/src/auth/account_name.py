import unicodedata

from auth.account_name_blankness import is_blank_after_stripping_invisibles
from shared.exceptions import ValidationException

# Cheap pre-normalization gate, on the raw input, before trim or NFC runs. Sized
# generously on purpose: NFD is longer than NFC, and a decomposed value must not
# be cut off before it has been given the chance to normalize down.
MAX_RAW_NAME_LENGTH = 256

# The stored bound, counted in CODE POINTS -- never bytes, never UTF-16 units. A
# 60-emoji name is 60 code points, 120 UTF-16 units and 240 UTF-8 bytes, and only
# one of those three numbers is the contract.
MAX_NAME_LENGTH = 60

# There is NO lower bound. Every value that normalizes to nothing is "clear the
# name", answered with 200 and a stored NULL -- a minimum of 1 would turn the
# documented way to remove a name into a 400.

INVALID_NAME_CODE = "INVALID_NAME"
INVALID_NAME_MESSAGE = "The name is not valid."

# A DIFFERENT code from INVALID_NAME, and that is the requirement, not a detail:
# `Email` raises one identical message at both its length stages, so no test there
# can prove the cheap gate ran at all. Two codes make "the pre-normalization gate
# fired" an observable fact. Named to read differently at a glance, too --
# NAME_TOO_LONG next to INVALID_NAME are both plausibly "too long" in a client's
# switch, and a client that conflates them reports the wrong limit to the user.
NAME_INPUT_TOO_LARGE_CODE = "NAME_INPUT_TOO_LARGE"
NAME_INPUT_TOO_LARGE_MESSAGE = "The submitted name is too large to process."


class AccountName:
    """A display name, normalized -- or the absence of one.

    Fail-closed like `Email`, and in the same order: a raw length cap before any
    expensive work, then rejection of characters that must never be stored, then
    normalization, then the stored bound. `.value` is `str | None`; `None` means
    the account has no display name, which is a legitimate outcome of a PATCH and
    not an error.

    Two things this refuses rather than repairs:

    `Cc` and `Cs` anywhere in the value are rejected, NOT stripped. A single NUL
    (U+0000) passes every "does it have visible characters" filter, is under both
    bounds, and is refused by Postgres's `text` type -- turning a documented 400
    into a 500 raised from the driver. Stripping would be worse than rejecting:
    it would silently store a different name than the one submitted.

    Blankness is a stricter predicate than `required_topic()` in
    `generation/generation_validation.py`, which this was modelled on. That one
    checks whitespace and category `Cf`; under it a name of one U+3164 (a Hangul
    filler, category `Lo`) is saved and renders as nothing -- exactly the empty
    identity the rule exists to prevent. See `account_name_blankness`.
    """

    def __init__(self, raw_value: object) -> None:
        self._value = _normalize(raw_value)

    @property
    def value(self) -> str | None:
        return self._value


def _normalize(raw_value: object) -> str | None:
    if raw_value is None:
        # JSON `null` is the explicit "clear my name" signal, so it is a value this
        # object accepts, NOT a non-string to refuse. It resolves to exactly what
        # `""` resolves to -- the two requests are indistinguishable downstream,
        # which is the contract. Ordered before the isinstance check below because
        # `None` would otherwise fall into it and answer 400 on the documented way
        # to remove a name.
        return None
    if not isinstance(raw_value, str):
        # `{"name": 123}`, `[]`, `{}`. Refused HERE rather than by Pydantic on
        # purpose: FastAPI's RequestValidationError answers 422 in a different
        # envelope that ECHOES THE REJECTED INPUT BACK. The request DTO types the
        # field permissively so the value reaches this line.
        raise _invalid_name()
    if len(raw_value) > MAX_RAW_NAME_LENGTH:
        raise ValidationException(
            error_code=NAME_INPUT_TOO_LARGE_CODE, message=NAME_INPUT_TOO_LARGE_MESSAGE
        )
    if _has_forbidden_category(raw_value):
        raise _invalid_name()
    normalized = unicodedata.normalize("NFC", raw_value.strip())
    if len(normalized) > MAX_NAME_LENGTH:
        raise _invalid_name()
    if is_blank_after_stripping_invisibles(normalized):
        return None
    return normalized


def _has_forbidden_category(raw_value: str) -> bool:
    # Checked on the RAW value, before trim and NFC: `strip()` removes whitespace
    # including the `Cc` control characters that happen to be whitespace (tab,
    # newline), and a value that is refused must be refused wherever the character
    # sits, not only where a trim would not have reached it.
    return any(unicodedata.category(char) in ("Cc", "Cs") for char in raw_value)


def _invalid_name() -> ValidationException:
    return ValidationException(error_code=INVALID_NAME_CODE, message=INVALID_NAME_MESSAGE)
