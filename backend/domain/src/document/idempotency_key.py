MIN_KEY_LENGTH = 1
MAX_KEY_LENGTH = 128


class IdempotencyKey:
    """Domain value object for the client-supplied Idempotency-Key header.

    Bounds come from documents_create.yaml (`minLength: 1, maxLength: 128`).
    Validated here rather than as a Pydantic Header constraint so a violation
    surfaces as this project's `{error_code, message}` shape rather than
    Pydantic's 422 envelope -- the same reason story 7's /verify dropped its
    `pattern=` from VerifyRequestDto and let the domain own the rule.

    The value is opaque: it is not parsed, not required to be a UUID, and not
    normalized. documents_create.yaml calls it a "client-generated key", so its
    only contract is equality with a previous key from the same owner.
    """

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str):
            raise ValueError("Invalid idempotency key.")
        if len(raw_value) < MIN_KEY_LENGTH or len(raw_value) > MAX_KEY_LENGTH:
            raise ValueError("Invalid idempotency key.")
        self._value = raw_value

    @property
    def value(self) -> str:
        return self._value
