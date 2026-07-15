from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRegisterCaseFoldedEmailLocaleInvariantAcceptance(AbstractBackendTest):
    """Scenario 2.4b: Case-fold uniqueness is locale-invariant.

    Given an account already exists for "user@example.ru"
    And the server's runtime locale is forced to a locale with non-standard
        casing rules (e.g. Turkish)
    When a registration request is submitted for "User@Example.ru"
    Then the response is still rejected as a duplicate, the same account
    And the case-fold does not diverge from the invariant-locale result
    """

    async def test_should_reject_registration_with_different_case_under_turkish_locale(
        self, auth_statements
    ):
        response = await auth_statements.given_duplicate_registration_with_different_case_under_turkish_locale()

        auth_statements.assert_rejected_as_duplicate(response)
