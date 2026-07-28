"""The UUID-format predicate shared by the generation Statements modules.

Two story-18 scenarios pin a UUID's SHAPE rather than its value, because the value is minted
somewhere the test cannot observe: scenario 1.1's `Idempotency-Key` comes from `crypto.randomUUID`
inside `createGeneration`, and scenario 1.2's polled run id comes back in the create POST's
response body, which `Network.requestWillBeSent` does not carry. Format is the only thing left
to assert, and it is the thing that rejects `''`, a constant placeholder, and `undefined`.

Exposed as a bool-returning predicate rather than an assertion so each call site keeps its own
failure message — one reports a whole list of keys, the other names the offending URL path. A
shared `assert_*` would have to flatten those into one generic wording.
"""

from uuid import UUID


def is_uuid(value: object) -> bool:
    """True when `value` parses as a UUID. Non-strings and None are simply not UUIDs."""
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True
