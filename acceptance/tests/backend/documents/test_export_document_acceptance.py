import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


class TestExportDocumentAcceptance(AbstractBackendTest):
    """Scenario 1.1: Export of a non-existent document is refused.

    Given an authenticated user
    When they export a document id that does not exist
    Then the request is refused as not found
    And no file is returned.
    """

    @pytest.mark.skip(reason="RED: export endpoint not implemented — no route serves "
                             "GET /api/v1/documents/{id}/export, so a non-existent id "
                             "returns Starlette's default {'detail':'Not Found'} instead "
                             "of the sanctioned {error_code:'NOT_FOUND'} shape")
    async def test_should_refuse_export_of_nonexistent_document(self, document_export_statements):
        response = await document_export_statements.given_authenticated_user_exports_nonexistent_document_as_pdf()

        document_export_statements.assert_refused_as_not_found(response)
        document_export_statements.assert_no_file_returned(response)
