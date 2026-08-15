"""`is_blank_after_stripping_invisibles` -- "does this render as anything?"

Each invisible code point is asserted on its own rather than in one mixed string.
A mixed string goes green as soon as ONE of the three strippers fires, and would
keep passing if the explicit denylist were deleted entirely -- which is the half
of the predicate nothing generic covers.

Every invisible character below is written as a code point and built with `chr()`,
for the same reason the production module does it: a literal would be a blank spot
in this file that an editor or a merge could drop without leaving a visible diff.
"""

import pytest

from auth.account_name import AccountName
from auth.account_name_blankness import (
    INVISIBLE_NON_FORMAT_CODE_POINTS,
    is_blank_after_stripping_invisibles,
)

_WHITESPACE_CODE_POINTS = (
    0x0020,  # SPACE
    0x00A0,  # NO-BREAK SPACE, category Zs
    0x2000,  # EN QUAD
    0x2009,  # THIN SPACE
    0x3000,  # IDEOGRAPHIC SPACE
    0x2028,  # LINE SEPARATOR, category Zl
)

_FORMAT_CODE_POINTS = (
    0x200B,  # ZERO WIDTH SPACE
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE
    0x00AD,  # SOFT HYPHEN
    0x200E,  # LEFT-TO-RIGHT MARK
    0x2060,  # WORD JOINER
)

_ALL_INVISIBLE = "".join(
    chr(point)
    for point in INVISIBLE_NON_FORMAT_CODE_POINTS + _WHITESPACE_CODE_POINTS + _FORMAT_CODE_POINTS
)


class TestBlankValues:
    def test_the_empty_string_is_blank(self):
        assert is_blank_after_stripping_invisibles("")

    @pytest.mark.parametrize("code_point", INVISIBLE_NON_FORMAT_CODE_POINTS)
    def test_each_invisible_non_format_character_is_blank_on_its_own(self, code_point: int):
        assert is_blank_after_stripping_invisibles(chr(code_point))

    @pytest.mark.parametrize("code_point", _WHITESPACE_CODE_POINTS)
    def test_each_whitespace_character_is_blank_on_its_own(self, code_point: int):
        assert is_blank_after_stripping_invisibles(chr(code_point))

    @pytest.mark.parametrize("code_point", _FORMAT_CODE_POINTS)
    def test_each_format_character_is_blank_on_its_own(self, code_point: int):
        assert is_blank_after_stripping_invisibles(chr(code_point))

    def test_a_string_of_every_invisible_kind_at_once_is_blank(self):
        assert is_blank_after_stripping_invisibles(_ALL_INVISIBLE)


class TestValuesThatDraw:
    @pytest.mark.parametrize("value", ["a", "é", "\U0001f600", ".", "-", "а"])
    def test_a_visible_character_is_not_blank(self, value: str):
        assert not is_blank_after_stripping_invisibles(value)

    @pytest.mark.parametrize("code_point", INVISIBLE_NON_FORMAT_CODE_POINTS)
    def test_one_visible_character_beside_an_invisible_one_is_enough(self, code_point: int):
        assert not is_blank_after_stripping_invisibles(chr(code_point) + "a")

    def test_a_combining_mark_that_is_not_on_the_denylist_still_counts_as_drawing(self):
        # COMBINING ACUTE ACCENT: it has no advance width of its own, but it is not
        # on the denylist, so the predicate must not claim it draws nothing.
        assert not is_blank_after_stripping_invisibles("́")


class TestAccountNameUsesThePredicate:
    @pytest.mark.parametrize("code_point", INVISIBLE_NON_FORMAT_CODE_POINTS)
    def test_a_name_of_one_invisible_character_clears_the_name(self, code_point: int):
        assert AccountName(chr(code_point)).value is None

    @pytest.mark.parametrize("code_point", _FORMAT_CODE_POINTS)
    def test_a_name_of_one_format_character_clears_the_name(self, code_point: int):
        assert AccountName(chr(code_point)).value is None

    def test_a_name_of_every_invisible_kind_at_once_clears_the_name(self):
        assert AccountName(_ALL_INVISIBLE).value is None

    def test_a_name_that_draws_something_survives_the_predicate(self):
        padded = chr(INVISIBLE_NON_FORMAT_CODE_POINTS[0]) + "Ada"

        assert AccountName(padded).value == padded
