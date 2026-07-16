import re


class VerificationCodeValue:
    """Domain value object for a validated email-verification code.

    Fail-closed: the rule is exactly `DIGIT_COUNT` ASCII digits (`[0-9]`), and
    anything else -- non-`str` input, wrong length, a non-digit character, a
    trailing newline, or a Unicode digit from outside ASCII -- is rejected
    rather than defaulted to valid.

    Two spellings are deliberately avoided here:

    - `str.isdigit()`, which accepts many Unicode decimal categories (e.g.
      Arabic-Indic "١٢٣٤٥٦") that this rule does not.
    - `re.match(r"^[0-9]{6}$", ...)`, because Python's `$` also matches before
      a trailing newline, so `"123456\\n"` would slip through. `fullmatch` is
      the house pattern (see `Email._DOMAIN_PATTERN`).

    The value is stored and returned as a `str` and is **never** coerced to
    `int`, so leading zeros ("042917") survive intact.

    `DIGIT_COUNT` is the single source of the 6-digit rule: `VerificationCode`
    imports it rather than restating it.
    """

    DIGIT_COUNT = 6

    _PATTERN = re.compile(rf"[0-9]{{{DIGIT_COUNT}}}")

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str) or not self._PATTERN.fullmatch(raw_value):
            raise ValueError("Invalid verification code.")
        self._value = raw_value

    @property
    def value(self) -> str:
        return self._value
