import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: GET /documents/{id} carries no 'page_settings' field — "
    "DocumentResponseDto does not define it"
)
class TestNeverConfiguredDocumentReadsAsUnconfigured(AbstractBackendTest):
    """Scenario 2.1: A never-configured document reads as unconfigured, not as the defaults.

    Given a document whose page settings have never been set
    When the caller reads it
    Then the page settings are reported as absent
    And the response does not carry a materialized default object.
    """

    async def test_never_configured_document_reads_as_unconfigured(
        self, document_page_settings_read_statements
    ):
        read = await document_page_settings_read_statements.given_owner_reads_a_never_configured_document()

        document_page_settings_read_statements.assert_page_settings_reported_as_absent(read)
        document_page_settings_read_statements.assert_no_materialized_default_object(read)
