import unicodedata

import pytest

from auth.password import Password

_BASE_PASSWORD = "Passw0rd1!"
_NFD_ACCENTED_PASSWORD = _BASE_PASSWORD + unicodedata.normalize("NFD", "é")
_NFC_ACCENTED_PASSWORD = _BASE_PASSWORD + unicodedata.normalize("NFC", "é")


class TestPasswordUnicodeNormalization:
    @pytest.mark.skip(reason="RED: Password.__init__ does not NFC-normalize raw_value")
    def test_combining_and_precomposed_forms_of_the_same_password_produce_identical_value(self):
        combining_form_password = Password(_NFD_ACCENTED_PASSWORD)
        precomposed_form_password = Password(_NFC_ACCENTED_PASSWORD)

        assert combining_form_password.value == _NFC_ACCENTED_PASSWORD
        assert precomposed_form_password.value == _NFC_ACCENTED_PASSWORD
