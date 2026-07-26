from tests.backend.abstract_backend_test import AbstractBackendTest


class TestExportDocumentAcceptance(AbstractBackendTest):
    """Scenario 1.1: Export of a non-existent document is refused.

    Given an authenticated user
    When they export a document id that does not exist
    Then the request is refused as not found
    And no file is returned.
    """

    async def test_should_refuse_export_of_nonexistent_document(self, document_export_statements):
        response = await document_export_statements.given_authenticated_user_exports_nonexistent_document_as_pdf()

        document_export_statements.assert_refused_as_not_found(response)
        document_export_statements.assert_no_file_returned(response)

    async def test_should_refuse_foreign_document_export_indistinguishably(
        self, document_export_statements
    ):
        """Scenario 1.2: a foreign-owned document exports as the sanctioned 404,
        byte-identical to the non-existent case, so ownership cannot be probed."""
        foreign = await document_export_statements.given_document_owned_by_another_account_exported_as_pdf()
        nonexistent = await document_export_statements.given_authenticated_user_exports_nonexistent_document_as_pdf()

        document_export_statements.assert_refused_as_not_found(foreign)
        document_export_statements.assert_no_file_returned(foreign)
        document_export_statements.assert_byte_identical_to_nonexistent_case(foreign, nonexistent)

    async def test_owner_can_export_own_document_distinguishably(self, document_export_statements):
        """Positive control for 1.2: the owner's own export must be distinguishable from
        the sanctioned 404, so the foreign-vs-nonexistent equality proves owner-scoping
        rather than degrading into a 404-equals-404 tautology."""
        own = await document_export_statements.given_owner_exports_their_own_document_as_pdf()

        document_export_statements.assert_distinguishable_from_not_found(own)
