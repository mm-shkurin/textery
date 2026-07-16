import pytest

from auth.verification_code_value import VerificationCodeValue

_INVALID_MESSAGE = "Invalid verification code."
_ARABIC_INDIC_SIX_DIGITS = "١٢٣٤٥٦"


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueNonStringRejection:
    def test_int_input_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue(42917)

        assert str(exc_info.value) == _INVALID_MESSAGE

    def test_none_input_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue(None)

        assert str(exc_info.value) == _INVALID_MESSAGE


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueLengthRejection:
    def test_five_digit_code_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue("12345")

        assert str(exc_info.value) == _INVALID_MESSAGE

    def test_seven_digit_code_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue("1234567")

        assert str(exc_info.value) == _INVALID_MESSAGE

    def test_empty_code_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue("")

        assert str(exc_info.value) == _INVALID_MESSAGE


@pytest.mark.skip(reason="RED: VerificationCodeValue.__init__ raises NotImplementedError")
class TestVerificationCodeValueNonDigitRejection:
    def test_code_with_a_letter_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue("12a456")

        assert str(exc_info.value) == _INVALID_MESSAGE

    def test_code_with_whitespace_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            VerificationCodeValue("12 456")

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
