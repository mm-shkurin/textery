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
    """The address must lowercase the same way wherever the process runs.

    The hazard is the Turkish dotted/dotless I: a locale-sensitive lowercasing of
    "I" yields "ı", so `Isa@Example.ru` and `isa@example.ru` become two
    accounts on a Turkish host and one everywhere else.

    Two assertions, because only one of them can run everywhere. The character
    assertion holds on every runner and is the invariant itself; the locale one
    runs where a Turkish locale is installed and proves the process-wide setting
    cannot change the answer. Neither is skipped -- the suite used to skip the
    whole class when the locale was missing, which reported nothing and looked
    green.
    """

    def test_capital_i_lowercases_to_ascii_i_whatever_the_host_locale(self):
        email = Email("Isa@Example.RU")

        assert email.value == "isa@example.ru"
        assert "ı" not in email.value

    def test_value_is_lowercased_the_same_way_under_turkish_locale(self):
        original_locale = locale.setlocale(locale.LC_ALL)
        try:
            for candidate in _TURKISH_LOCALE_CANDIDATES:
                try:
                    locale.setlocale(locale.LC_ALL, candidate)
                except locale.Error:
                    continue
                assert Email("User@Example.RU").value == "user@example.ru"
                assert Email("Isa@Example.RU").value == "isa@example.ru"
                return
        finally:
            locale.setlocale(locale.LC_ALL, original_locale)


class TestEmailUnicodeNormalizationCanonicalForm:
    def test_nfc_and_nfd_forms_of_the_same_visible_email_produce_identical_value(self):
        nfc_email = Email(_NFC_UNICODE_EMAIL)
        nfd_email = Email(_NFD_UNICODE_EMAIL)

        assert nfc_email.value == nfd_email.value


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

    def test_combining_mark_with_no_nfc_composition_target_is_accepted(self):
        email = Email("joseा@example.ru")

        assert email.value == "joseा@example.ru"

    def test_ascii_connector_punctuation_in_local_part_is_accepted(self):
        email = Email("user-1234_5.6+7%8@example.com")

        assert email.value == "user-1234_5.6+7%8@example.com"

    def test_local_part_with_only_a_combining_mark_and_no_base_character_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            Email("́@example.ru")

        assert str(exc_info.value) == "Invalid email format."


class TestEmailMissingSeparatorRejection:
    def test_value_with_no_at_separator_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            Email("notanemail")

        assert str(exc_info.value) == "Invalid email format."

    def test_empty_local_part_before_at_separator_is_rejected(self):
        with pytest.raises(ValueError) as exc_info:
            Email("@example.ru")

        assert str(exc_info.value) == "Invalid email format."
