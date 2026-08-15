"""`AccountName` -- what gets stored, what gets refused, and IN WHICH ORDER.

The order is the part worth testing. Two different error codes exist precisely so
that "the cheap raw-length gate ran before normalization" is observable, and a
test that only checked "it was refused" would pass against a pipeline with the
stages in either order.
"""

import unicodedata

import pytest

from auth.account_name import (
    INVALID_NAME_CODE,
    MAX_NAME_LENGTH,
    MAX_RAW_NAME_LENGTH,
    NAME_INPUT_TOO_LARGE_CODE,
    AccountName,
)
from shared.exceptions import ValidationException

# NFD "é" is two code points; its NFC form is one. Every case that needs the raw
# form to be longer than the normalized one is built from this.
_E_ACUTE_NFD = unicodedata.normalize("NFD", "é")
_E_ACUTE_NFC = unicodedata.normalize("NFC", "é")


def _refusal_code(raw_value: object) -> str:
    with pytest.raises(ValidationException) as refusal:
        AccountName(raw_value)
    return refusal.value.error_code


class TestStoresANormalizedName:
    def test_keeps_an_ordinary_name(self):
        assert AccountName("Ada Lovelace").value == "Ada Lovelace"

    def test_trims_leading_and_trailing_whitespace(self):
        assert AccountName("  Ada  ").value == "Ada"

    def test_composes_a_decomposed_name_to_its_nfc_form(self):
        assert AccountName(_E_ACUTE_NFD + "cole").value == _E_ACUTE_NFC + "cole"

    def test_stores_a_name_whose_nfc_form_is_shorter_than_the_value_submitted(self):
        raw_value = _E_ACUTE_NFD * MAX_NAME_LENGTH

        stored = AccountName(raw_value).value

        assert stored == _E_ACUTE_NFC * MAX_NAME_LENGTH
        assert len(stored) < len(raw_value)


class TestTheAbsenceOfAName:
    def test_null_clears_the_name(self):
        assert AccountName(None).value is None

    def test_the_empty_string_clears_the_name_indistinguishably_from_null(self):
        assert AccountName("").value == AccountName(None).value

    def test_whitespace_only_clears_the_name(self):
        # Spaces and a NO-BREAK SPACE. A tab would not reach this outcome: it is
        # category Cc, which `AccountName` refuses outright rather than trims.
        assert AccountName("     ").value is None


class TestLengthBounds:
    def test_accepts_a_name_of_exactly_sixty_code_points(self):
        assert AccountName("a" * MAX_NAME_LENGTH).value == "a" * MAX_NAME_LENGTH

    def test_refuses_a_name_one_code_point_over_the_stored_bound(self):
        assert _refusal_code("a" * (MAX_NAME_LENGTH + 1)) == INVALID_NAME_CODE

    def test_counts_astral_characters_as_one_code_point_each(self):
        emoji = "\U0001f600"

        assert AccountName(emoji * MAX_NAME_LENGTH).value == emoji * MAX_NAME_LENGTH

    def test_refuses_one_astral_character_too_many(self):
        assert _refusal_code("\U0001f600" * (MAX_NAME_LENGTH + 1)) == INVALID_NAME_CODE

    def test_accepts_a_decomposed_name_landing_exactly_on_the_bound_once_composed(self):
        raw_value = _E_ACUTE_NFD * MAX_NAME_LENGTH

        assert len(AccountName(raw_value).value) == MAX_NAME_LENGTH

    def test_refuses_a_decomposed_name_one_over_the_bound_once_composed(self):
        raw_value = _E_ACUTE_NFD * (MAX_NAME_LENGTH + 1)

        assert _refusal_code(raw_value) == INVALID_NAME_CODE

    def test_measures_the_bound_after_trimming_rather_than_before(self):
        padded = "  " + "a" * MAX_NAME_LENGTH + "  "

        assert AccountName(padded).value == "a" * MAX_NAME_LENGTH


class TestTheRawGateRunsFirst:
    def test_accepts_a_raw_value_of_exactly_the_raw_ceiling(self):
        # Two hundred and fifty-six spaces: past the raw gate, then blank.
        assert AccountName(" " * MAX_RAW_NAME_LENGTH).value is None

    def test_refuses_a_raw_value_one_over_the_raw_ceiling_with_its_own_code(self):
        assert _refusal_code(" " * (MAX_RAW_NAME_LENGTH + 1)) == NAME_INPUT_TOO_LARGE_CODE

    def test_a_decomposed_name_that_would_fit_after_composition_is_still_refused_raw(self):
        """Two hundred characters, submitted decomposed, arriving as four hundred.

        Its NFC form is well inside every bound -- so the refusal can only come
        from a gate that ran BEFORE normalization, and the code proves which one.
        """
        raw_value = _E_ACUTE_NFD * 200
        assert len(raw_value) > MAX_RAW_NAME_LENGTH
        assert len(unicodedata.normalize("NFC", raw_value)) <= MAX_NAME_LENGTH * 4

        assert _refusal_code(raw_value) == NAME_INPUT_TOO_LARGE_CODE

    def test_the_raw_gate_answers_before_the_forbidden_category_check(self):
        oversized_with_a_control_character = "\x00" + "a" * MAX_RAW_NAME_LENGTH

        assert _refusal_code(oversized_with_a_control_character) == NAME_INPUT_TOO_LARGE_CODE


class TestForbiddenCategories:
    @pytest.mark.parametrize("control", ["\x00", "\x01", "\t", "\n", "\r", "\x1f", "\x7f"])
    def test_refuses_a_control_character_anywhere_in_the_value(self, control: str):
        assert _refusal_code("Ada" + control + "Lovelace") == INVALID_NAME_CODE

    @pytest.mark.parametrize("control", ["\x00", "\t", "\n"])
    def test_refuses_a_control_character_a_trim_would_have_removed(self, control: str):
        assert _refusal_code(control + "Ada" + control) == INVALID_NAME_CODE

    @pytest.mark.parametrize("surrogate", ["\ud800", "\udbff", "\udc00", "\udfff"])
    def test_refuses_a_lone_surrogate_anywhere_in_the_value(self, surrogate: str):
        assert _refusal_code("Ada" + surrogate) == INVALID_NAME_CODE

    def test_refuses_a_value_made_only_of_a_control_character(self):
        assert _refusal_code("\x00") == INVALID_NAME_CODE


class TestNonStrings:
    @pytest.mark.parametrize("raw_value", [123, 1.5, True, [], {}, (), object()])
    def test_refuses_a_value_that_is_not_a_string(self, raw_value: object):
        assert _refusal_code(raw_value) == INVALID_NAME_CODE

    def test_refuses_bytes_rather_than_decoding_them(self):
        assert _refusal_code(b"Ada") == INVALID_NAME_CODE
