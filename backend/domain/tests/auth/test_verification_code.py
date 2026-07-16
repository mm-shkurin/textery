import re
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from auth.verification_code import VerificationCode

_ASCII_SIX_DIGITS = re.compile(r"^[0-9]{6}$")
_CREATED_AT = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)


def _generate() -> VerificationCode:
    return VerificationCode.generate(
        id=uuid4(),
        account_id=uuid4(),
        created_at=_CREATED_AT,
    )


class TestVerificationCodeGenerateShape:
    """Guards the /register path: generate().code must stay a plain `str`.

    If it ever yields a value object instead, matches() compares that object
    against the submitted `str` and returns False for every correct code -- a
    silent, total verification outage that no other test would catch.
    """

    def test_generated_code_is_a_str(self):
        generated = _generate()

        assert isinstance(generated.code, str)

    def test_generated_code_is_six_ascii_digits(self):
        generated = _generate()

        assert _ASCII_SIX_DIGITS.fullmatch(generated.code) is not None, (
            f"expected exactly six ASCII digits, got {generated.code!r}"
        )

    def test_generated_code_matches_itself(self):
        generated = _generate()

        assert generated.matches(generated.code) is True


class TestVerificationCodeGenerateLeadingZeros:
    def test_low_random_draw_is_zero_padded_to_six_characters(self, monkeypatch):
        monkeypatch.setattr(secrets, "randbelow", lambda _upper_bound: 42917)

        generated = _generate()

        assert generated.code == "042917"
