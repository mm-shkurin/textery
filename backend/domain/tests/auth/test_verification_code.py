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

    def test_generated_code_matches_an_equal_str_built_independently(self, monkeypatch):
        # Compared against a separately-constructed literal, never against
        # generated.code -- `matches(generated.code)` is `self._code == self._code`,
        # true by identity for any type, including the value object this guards against.
        monkeypatch.setattr(secrets, "randbelow", lambda _upper_bound: 42917)

        generated = _generate()

        assert generated.matches("042917") is True


class TestVerificationCodeGenerateEntropy:
    """Guards the /register path: the random draw's upper bound must stay 10**6.

    The shape guards above are all blind to this. green-usecase is instructed to
    delete _CODE_MODULUS and import the digit count from VerificationCodeValue --
    the natural typo, `randbelow(_CODE_DIGITS)`, draws 0-5 and formats to "000003",
    which is a str, is six ASCII digits, matches, and round-trips through String(6).
    Every existing guard passes while entropy collapses from 1,000,000 to 6.

    The bound is restated as a literal rather than imported from the code under
    test: importing it would make the assertion tautological, and this guard must
    stay live (never skip-marked) through the very refactor it exists to catch.
    """

    def test_random_draw_is_bounded_by_the_full_six_digit_space(self, monkeypatch):
        received_bounds = []

        def _recording_randbelow(upper_bound: int) -> int:
            received_bounds.append(upper_bound)
            return 42917

        monkeypatch.setattr(secrets, "randbelow", _recording_randbelow)

        _generate()

        assert received_bounds == [1_000_000]


class TestVerificationCodeGenerateLeadingZeros:
    def test_low_random_draw_is_zero_padded_to_six_characters(self, monkeypatch):
        monkeypatch.setattr(secrets, "randbelow", lambda _upper_bound: 42917)

        generated = _generate()

        assert generated.code == "042917"
