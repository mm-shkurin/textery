"""The bounds a reported `payload` has to satisfy before it is stored.

Three bounds rather than one, and they are deliberately not redundant
(`endpoints.md` § "Every bound is a number, with its unit"):

* 4096 **bytes** of serialized JSON -- bytes, not code points, because the cap
  guards what the column stores and what the transport carried, and one emoji is
  four of the former and one of the latter.
* 8 levels of nesting -- 4 KiB of `[[[[...]]]]` is comfortably under the byte cap
  and still meets Python's decoder as a `RecursionError`, i.e. a 500 on a request
  that passed validation.
* 64 keys in total, counted across every nested object -- a flat 4 KiB body can
  hold thousands of one-character keys, and each becomes a JSONB key Story 15
  pays for on every read.

The refusal names no value and echoes nothing back: this is the product's only
tokenless route, so its errors reach anyone (Security §3.3).
"""

import json
from typing import Any

from shared import limits
from shared.exceptions import ValidationException

MAX_SERIALIZED_BYTES = limits.MAX_PAYLOAD_SERIALIZED_BYTES
MAX_DEPTH = 8
MAX_KEYS = 64

INVALID_PAYLOAD = "INVALID_PAYLOAD"
NUL_ESCAPE = "\\u0000"
_REFUSAL = "The event payload is not acceptable."


def validate_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return the payload to store: `{}` for absent, explicit null and `{}` alike."""
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise _refused()
    _refuse_unstorable(payload)
    if _depth_of(payload) > MAX_DEPTH:
        raise _refused()
    if _key_count_of(payload) > MAX_KEYS:
        raise _refused()
    return payload


def _refuse_unstorable(payload: dict[str, Any]) -> None:
    """Refuse what the column cannot hold, and what is too big once serialized.

    `json.dumps` is the same encoding the driver will use, so a value it cannot
    render (a lone surrogate, a non-JSON type) is refused here with the canonical
    400 rather than surfacing as a driver error and a 500 further down.
    """
    try:
        rendered = json.dumps(payload, ensure_ascii=False)
        serialized = rendered.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise _refused() from error
    # Postgres refuses NUL in text and in JSONB strings alike. `json.dumps`
    # renders it as the six-character escape rather than as the byte, so that is
    # what is searched for: looking for the raw byte here would never match and
    # the refusal would arrive from the driver as a 500 instead.
    if NUL_ESCAPE in rendered:
        raise _refused()
    if len(serialized) > MAX_SERIALIZED_BYTES:
        raise _refused()


def _depth_of(value: Any, level: int = 1) -> int:
    """Nesting depth, walked iteratively-by-recursion over containers only.

    The walk itself is bounded by the same limit it measures: it stops descending
    once past `MAX_DEPTH`, so a pathological body cannot make the *validator* the
    thing that overflows the stack.
    """
    if level > MAX_DEPTH:
        return level
    children = _children_of(value)
    if not children:
        return level
    return max(_depth_of(child, level + 1) for child in children)


def _key_count_of(value: Any) -> int:
    keys = len(value) if isinstance(value, dict) else 0
    return keys + sum(_key_count_of(child) for child in _children_of(value))


def _children_of(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, list):
        return value
    return []


def _refused() -> ValidationException:
    return ValidationException(message=_REFUSAL, error_code=INVALID_PAYLOAD)
