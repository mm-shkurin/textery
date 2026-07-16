import unicodedata

from statements.register_statements import RegisterStatements

_BASE_PASSWORD = "Passw0rd1!"
_NFD_ACCENTED_PASSWORD = _BASE_PASSWORD + unicodedata.normalize("NFD", "é")
_NFC_ACCENTED_PASSWORD = _BASE_PASSWORD + unicodedata.normalize("NFC", "é")


class TestRegisterUsecasePasswordConfirmationNormalization:
    """Scenario 2.7: NFD/NFC forms of the same logical password must not mismatch.

    Given a registration request whose password and confirm_password are the
    same visible password but arrive in different Unicode normalization forms
    (e.g. password manager autofill vs. manual retype)
    When the client submits the request
    Then registration succeeds rather than raising a false PASSWORD_MISMATCH
    """

    async def test_should_accept_password_and_confirmation_in_different_normalization_forms(
        self, register_statements: RegisterStatements
    ):
        await register_statements.register_with_differently_normalized_password_and_confirmation(
            password=_NFD_ACCENTED_PASSWORD, confirm_password=_NFC_ACCENTED_PASSWORD
        )
        register_statements.assert_registration_succeeded()

    async def test_should_persist_password_in_its_nfc_normalized_form(
        self, register_statements: RegisterStatements
    ):
        await register_statements.register_with_differently_normalized_password_and_confirmation(
            password=_NFD_ACCENTED_PASSWORD, confirm_password=_NFD_ACCENTED_PASSWORD
        )
        register_statements.assert_password_hashed_from_normalized_form(_NFC_ACCENTED_PASSWORD)
