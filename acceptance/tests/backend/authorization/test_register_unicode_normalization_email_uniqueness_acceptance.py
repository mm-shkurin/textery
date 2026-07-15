from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterUnicodeNormalizationEmailUniquenessAcceptance(AbstractBackendTest):
    """Scenario 2.4c: Unicode-normalization uniqueness for email.

    Given an account already exists for an email whose local part is a
        precomposed accented character (NFC form)
    When a registration request is submitted for the visually identical
        email written with a combining-character sequence (NFD form)
    Then the response is rejected as a duplicate, the same account

    Current gap: Email's format regex (backend/domain/src/auth/email.py)
    only accepts ASCII local-parts, so the NFC-form email that is meant to
    establish the "account already exists" precondition is itself rejected
    with 400 INVALID_EMAIL before the duplicate-check path is ever reached.
    """

    async def test_should_reject_registration_with_unicode_normalized_duplicate_email(
        self, auth_statements
    ):
        response = await auth_statements.given_unicode_normalized_duplicate_registration()

        auth_statements.assert_rejected_as_duplicate(response)
