import re
import unicodedata

MAX_EMAIL_LENGTH = 254

_DOMAIN_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_DOMAIN_PATTERN = re.compile(rf"^(?:{_DOMAIN_LABEL}\.)+[A-Za-z]{{2,}}$")
_ACCEPTED_UNICODE_CATEGORY_PREFIXES = ("L", "Mn", "Mc", "Me", "Nd")


class Email:
    """Domain value object for a validated email address.

    Fail-closed: any input that is not a clean match of the bounded
    validation checks is rejected rather than defaulted to valid. Length
    is capped before normalization/validation runs so an overlong or
    adversarial input never reaches the more expensive checks.

    Pipeline: length cap -> NFC normalize -> character-class/structural
    validation -> case-fold. The local-part (before "@") accepts only
    Unicode Letter, Mark, and Decimal_Number categories; the domain label
    stays ASCII-only.
    """

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str) or not raw_value or len(raw_value) > MAX_EMAIL_LENGTH:
            raise ValueError("Invalid email format.")
        normalized_value = unicodedata.normalize("NFC", raw_value)
        if not self._is_valid(normalized_value):
            raise ValueError("Invalid email format.")
        self._value = normalized_value.lower()

    @staticmethod
    def _is_valid(normalized_value: str) -> bool:
        local_part, separator, domain = normalized_value.partition("@")
        if not separator or not local_part:
            return False
        if not all(Email._is_accepted_local_part_char(char) for char in local_part):
            return False
        return bool(_DOMAIN_PATTERN.fullmatch(domain))

    @staticmethod
    def _is_accepted_local_part_char(char: str) -> bool:
        category = unicodedata.category(char)
        return category.startswith(_ACCEPTED_UNICODE_CATEGORY_PREFIXES)

    @property
    def value(self) -> str:
        return self._value
