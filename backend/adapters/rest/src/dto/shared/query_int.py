"""A query-string integer, parsed strictly at the transport boundary.

Every list endpoint in this API refuses a bad `?limit=` with the product's own
`{error_code, message}` envelope. That is only true if the router never declares
the parameter as `int`: a Pydantic annotation refuses the value first, in its
own `{"detail": ...}` 422, so `?limit=abc` and `?limit=999` -- the same mistake
twice -- came back in two different shapes and a client could not branch on
either.

The bounds are NOT here. This turns text into a number or refuses; whether the
number is one this endpoint will serve stays with the domain's `PageRequest`,
which is shared by every history list so the limits cannot drift between them.
"""

from shared.exceptions import ValidationException


def exact_int(raw: str | None, default: int, error_code: str, name: str) -> int:
    """An exact decimal integer, or a refusal in the canonical envelope.

    `int(raw)` alone is too permissive for this contract: it accepts `+1`, `_1`
    and surrounding whitespace, and `float(raw)` would accept `2.5` and `1e3`.
    The contract says exact decimal integer, so the string is checked before it
    is converted rather than after.

    An omitted parameter takes the default; a present-but-empty one does not --
    `?limit=` is a client that sent the parameter and named nothing.
    """
    if raw is None:
        return default
    candidate = raw[1:] if raw.startswith("-") else raw
    if candidate == "" or not candidate.isascii() or not candidate.isdigit():
        raise ValidationException(
            message=f"{name} must be an exact decimal integer.",
            error_code=error_code,
        )
    return int(raw)
