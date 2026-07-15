import unicodedata

import pytest

from auth.password import MAX_PASSWORD_LENGTH, Password

# A combining-mark suffix that inflates the NFD form's code-point count
# relative to its NFC form. Used to pin the validation-order decision:
# length-cap must run on the RAW input BEFORE normalization, matching
# Email's established pipeline order (length cap -> normalize -> validate).
_ACCENTED_CHAR_NFD = unicodedata.normalize("NFD", "é")
_ACCENTED_CHAR_NFC = unicodedata.normalize("NFC", "é")


class TestPasswordValidationOrder:
    def test_rejects_raw_input_exceeding_max_length_even_though_nfc_form_would_fit(self):
        base = "Aa1!" + "a" * (MAX_PASSWORD_LENGTH - 4 - len(_ACCENTED_CHAR_NFD))
        raw_value = base + _ACCENTED_CHAR_NFD * 2
        assert len(raw_value) > MAX_PASSWORD_LENGTH

        with pytest.raises(ValueError):
            Password(raw_value)

    def test_accepts_password_whose_nfc_normalized_form_is_within_max_length(self):
        base = "Aa1!" + "a" * (MAX_PASSWORD_LENGTH - 4 - len(_ACCENTED_CHAR_NFC))
        raw_value = base + _ACCENTED_CHAR_NFC
        assert len(raw_value) <= MAX_PASSWORD_LENGTH

        password = Password(raw_value)

        assert password.value == unicodedata.normalize("NFC", raw_value)
