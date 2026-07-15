import pytest

from auth.email import Email


class TestEmailNormalization:
    def test_value_is_lowercased_for_mixed_case_input(self):
        email = Email("User@Example.RU")

        assert email.value == "user@example.ru"
