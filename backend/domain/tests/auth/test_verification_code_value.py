import pytest

from auth.verification_code_value import VerificationCodeValue

_INVALID_MESSAGE = "Invalid verification code."
_ARABIC_INDIC_SIX_DIGITS = "١٢٣٤٥٦"


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueNonStringRejection:
    @pytest.mark.parametrize("raw_input", [42917, None], ids=["int", "none"])
    def test_non_string_input_is_rejected(self, raw_input):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue(raw_input)

        assert str(exc_info.value) == _INVALID_MESSAGE


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueLengthRejection:
    @pytest.mark.parametrize(
        "raw_input", ["12345", "1234567", ""], ids=["five_digits", "seven_digits", "empty"]
    )
    def test_code_of_wrong_length_is_rejected(self, raw_input):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue(raw_input)

        assert str(exc_info.value) == _INVALID_MESSAGE


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueNonDigitRejection:
    @pytest.mark.parametrize("raw_input", ["12a456", "12 456"], ids=["letter", "whitespace"])
    def test_code_with_a_non_digit_is_rejected(self, raw_input):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue(raw_input)

        assert str(exc_info.value) == _INVALID_MESSAGE


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueUnicodeDigitRejection:
    """ASCII [0-9] only -- str.isdigit() accepts many Unicode digit
    categories and is the obvious wrong implementation here."""

    def test_arabic_indic_six_digit_code_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue(_ARABIC_INDIC_SIX_DIGITS)

        assert str(exc_info.value) == _INVALID_MESSAGE


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueAcceptance:
    def test_six_digit_code_with_leading_zeros_is_accepted_intact(self):
        code = VerificationCodeValue("042917")

        assert code.value == "042917"

    def test_accepted_value_is_a_str_never_coerced_to_int(self):
        code = VerificationCodeValue("042917")

        assert isinstance(code.value, str)
