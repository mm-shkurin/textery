import pytest

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


class TestExportDocumentAsPdf(AbstractBackendTest):
    """Scenario 2.1: A document exports as a valid PDF.

    Given a document owned by the caller
    When they export it as pdf
    Then the response is a valid PDF with the pdf content type
    And is delivered as an attachment.
    """

    async def test_owner_exports_own_document_as_valid_pdf_attachment(
        self, document_export_statements
    ):
        response = await document_export_statements.given_owner_exports_their_own_document_as_pdf()

        document_export_statements.assert_valid_pdf_attachment(response)


class TestExportDocumentAsDocx(AbstractBackendTest):
    """Scenario 2.2: A document exports as a valid DOCX.

    Given a document owned by the caller
    When they export it as docx
    Then the response is a valid DOCX with the wordprocessingml content type
    And is delivered as an attachment.
    """

    async def test_owner_exports_own_document_as_valid_docx_attachment(
        self, document_export_docx_statements
    ):
        response = await document_export_docx_statements.given_owner_exports_their_own_document_as_docx()

        document_export_docx_statements.assert_valid_docx_attachment(response)


class TestExportDoesNotMutateDocument(AbstractBackendTest):
    """Scenario 2.4: Export does not mutate the document.

    Given a document owned by the caller at a known version
    When they export it
    Then the document version is unchanged afterwards.
    """

    async def test_export_leaves_document_version_unchanged(
        self, document_export_no_mutation_statements
    ):
        snapshot = (
            await document_export_no_mutation_statements.given_owner_document_read_exported_and_reread()
        )

        document_export_no_mutation_statements.assert_version_unchanged(snapshot)
        document_export_no_mutation_statements.assert_not_mutated(snapshot)


class TestExportFilenameFromCyrillicTitle(AbstractBackendTest):
    """Scenario 3.1: The filename is derived from the title, encoded for Cyrillic.

    Given a document whose title contains Cyrillic characters
    When it is exported
    Then the attachment filename is RFC 5987-encoded and reflects the title.
    """

    async def test_export_filename_is_rfc5987_encoded_from_cyrillic_title(
        self, document_export_filename_statements
    ):
        response = await document_export_filename_statements.given_owner_exports_document_with_cyrillic_title_as_pdf()

        document_export_filename_statements.assert_filename_rfc5987_encoded_from_title(
            response
        )


class TestExportDocumentFormatGuard(AbstractBackendTest):
    """Scenario 1.3: An unsupported or missing format is refused.

    Given a document owned by the caller
    When they export it with a format that is neither pdf nor docx, or with no format
    Then the request is refused as unprocessable
    And no file is returned.
    """

    @pytest.mark.parametrize(
        "export_format", ["xml", None], ids=["unsupported_format", "missing_format"]
    )
    async def test_should_refuse_unsupported_or_missing_format(
        self, document_export_format_statements, export_format
    ):
        response = await document_export_format_statements.given_owner_exports_own_document_with_format(
            export_format
        )

        document_export_format_statements.assert_refused_as_unprocessable(response)
        document_export_format_statements.assert_no_file_returned(response)
