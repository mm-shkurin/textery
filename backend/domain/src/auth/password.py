import re

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

_DIGIT_PATTERN = re.compile(r"\d")
_UPPERCASE_PATTERN = re.compile(r"[A-Z]")
_LOWERCASE_PATTERN = re.compile(r"[a-z]")
_SPECIAL_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9]")


class Password:
    """Domain value object for a password meeting the password policy.

    Fail-closed: any input that does not satisfy every policy rule
    (length bounds, digit, uppercase, lowercase, special character) is
    rejected rather than defaulted to valid.
    """

    def __init__(self, raw_value: str) -> None:
        if not self._is_valid(raw_value):
            raise ValueError("Invalid password.")
        self._value = raw_value

    @staticmethod
    def _is_valid(raw_value: str) -> bool:
        if not isinstance(raw_value, str):
            return False
        if len(raw_value) < MIN_PASSWORD_LENGTH or len(raw_value) > MAX_PASSWORD_LENGTH:
            return False
        if not _DIGIT_PATTERN.search(raw_value):
            return False
        if not _UPPERCASE_PATTERN.search(raw_value):
            return False
        if not _LOWERCASE_PATTERN.search(raw_value):
            return False
        if not _SPECIAL_CHAR_PATTERN.search(raw_value):
            return False
        return True

    @property
    def value(self) -> str:
        return self._value
