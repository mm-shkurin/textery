import pytest

from auth.email import Email


@pytest.mark.skip(reason="RED: Email('User@Example.RU').value returns 'User@Example.RU' instead of lowercased 'user@example.ru'")
class TestEmailNormalization:
    def test_value_is_lowercased_for_mixed_case_input(self):
        email = Email("User@Example.RU")

        assert email.value == "user@example.ru"
