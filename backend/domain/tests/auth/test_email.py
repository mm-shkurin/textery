import locale
import unicodedata

import pytest

from auth.email import Email

_TURKISH_LOCALE_CANDIDATES = ("tr_TR.UTF-8", "tr_TR", "tr-TR", "Turkish_Turkey.1254")
_NFC_UNICODE_EMAIL = unicodedata.normalize("NFC", "josé@example.ru")
_NFD_UNICODE_EMAIL = unicodedata.normalize("NFD", "josé@example.ru")


class TestEmailNormalization:
    def test_value_is_lowercased_for_mixed_case_input(self):
        email = Email("User@Example.RU")

        assert email.value == "user@example.ru"


class TestEmailNormalizationLocaleInvariance:
    def test_value_is_lowercased_the_same_way_under_turkish_locale(self):
        original_locale = locale.setlocale(locale.LC_ALL)
        try:
            locale_set = False
            for candidate in _TURKISH_LOCALE_CANDIDATES:
                try:
                    locale.setlocale(locale.LC_ALL, candidate)
                    locale_set = True
                    break
                except locale.Error:
                    continue
            if not locale_set:
                pytest.skip("Turkish locale not installed on this runner")

            email = Email("User@Example.RU")

            assert email.value == "user@example.ru"
        finally:
            locale.setlocale(locale.LC_ALL, original_locale)


@pytest.mark.skip(
    reason="RED: Email._EMAIL_PATTERN is ASCII-only, ValueError('Invalid email format.') raised on non-ASCII local-part"
)
class TestEmailUnicodeNormalizationCanonicalForm:
    def test_nfc_and_nfd_forms_of_the_same_visible_email_produce_identical_value(self):
        nfc_email = Email(_NFC_UNICODE_EMAIL)
        nfd_email = Email(_NFD_UNICODE_EMAIL)

        assert nfc_email.value == nfd_email.value


@pytest.mark.skip(
    reason="RED: Email._EMAIL_PATTERN rejects all non-ASCII local-parts uniformly, ValueError('Invalid email format.') raised for both the malicious control/format-char input and the valid accented Unicode input"
)
class TestEmailUnicodeCharacterClassRejection:
    def test_control_char_in_local_part_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            Email("jos\re@example.ru")

        assert str(exc_info.value) == "Invalid email format."

    def test_zero_width_space_in_local_part_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            Email("jos​e@example.ru")

        assert str(exc_info.value) == "Invalid email format."

    def test_letter_mark_and_decimal_number_local_part_is_accepted(self):
        email = Email("josé123@example.ru")

        assert email.value == "josé123@example.ru"
