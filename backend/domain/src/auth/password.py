import re
import unicodedata

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
    rejected rather than defaulted to valid. Length is capped on the raw
    input before normalization runs, mirroring Email's pipeline: length
    cap -> NFC normalize -> character-class/content validation.
    """

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str) or len(raw_value) > MAX_PASSWORD_LENGTH:
            raise ValueError("Invalid password.")
        normalized_value = unicodedata.normalize("NFC", raw_value)
        if not self._is_valid(normalized_value):
            raise ValueError("Invalid password.")
        self._value = normalized_value

    @staticmethod
    def _is_valid(normalized_value: str) -> bool:
        if (
            len(normalized_value) < MIN_PASSWORD_LENGTH
            or len(normalized_value) > MAX_PASSWORD_LENGTH
        ):
            return False
        if not _DIGIT_PATTERN.search(normalized_value):
            return False
        if not _UPPERCASE_PATTERN.search(normalized_value):
            return False
        if not _LOWERCASE_PATTERN.search(normalized_value):
            return False
        return bool(_SPECIAL_CHAR_PATTERN.search(normalized_value))

    @property
    def value(self) -> str:
        return self._value
