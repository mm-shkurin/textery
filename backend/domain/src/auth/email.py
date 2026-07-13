import re

MAX_EMAIL_LENGTH = 254

_EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


class Email:
    """Domain value object for a validated email address.

    Fail-closed: any input that is not a clean match of the bounded,
    non-backtracking format check is rejected rather than defaulted to
    valid. Length is capped before the format check runs so an overlong
    or adversarial input never reaches the regex.
    """

    def __init__(self, raw_value: str) -> None:
        if not self._is_valid(raw_value):
            raise ValueError("Invalid email format.")
        self._value = raw_value

    @staticmethod
    def _is_valid(raw_value: str) -> bool:
        if not isinstance(raw_value, str):
            return False
        if not raw_value or len(raw_value) > MAX_EMAIL_LENGTH:
            return False
        if " " in raw_value:
            return False
        if "@@" in raw_value:
            return False
        return bool(_EMAIL_PATTERN.fullmatch(raw_value))

    @property
    def value(self) -> str:
        return self._value
