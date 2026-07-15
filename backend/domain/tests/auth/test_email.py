import locale

import pytest

from auth.email import Email

_TURKISH_LOCALE_CANDIDATES = ("tr_TR.UTF-8", "tr_TR", "tr-TR", "Turkish_Turkey.1254")


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
