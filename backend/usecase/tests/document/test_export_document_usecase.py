"""ExportDocument: the read side of exporting to PDF/DOCX.

Scenario 1.1 -- exporting a document id that does not exist is refused. The
usecase returns None (the refusal signal the router turns into a 404) rather
than raising, mirroring GetDocument: absent and foreign both collapse to None
because the repository filters on owner_id in SQL.

Scenario 1.3 -- an unsupported or missing format is refused. The format is
validated by `ExportFormat.parse` **before** the owner-scoped fetch, so a bad
format raises `ValidationException(INVALID_FORMAT)` regardless of whether the
target document exists -- it discloses nothing about the document. The positive
control (a valid `pdf`/`docx` export returns the stored document) is
non-negotiable: without it the negative cases pass tautologically against a
guard that refuses everything.
"""

from uuid import uuid4

import pytest

from document.export_document import ExportDocument
from shared.exceptions import ValidationException
from statements.document_fakes import FakeDocumentRepository, seeded, stored_document


@pytest.mark.skip(
    reason="RED: ExportDocument.execute() takes no 'format' arg and ExportFormat VO absent"
)
class TestExportDocument:
    async def test_should_answer_none_for_a_non_existent_document(self):
        found = await ExportDocument(FakeDocumentRepository()).execute(
            document_id=uuid4(), owner_id=uuid4(), format="pdf"
        )

        assert found is None

    @pytest.mark.parametrize(
        "bad_format",
        ["xml", None, "", "PDF", " pdf "],
        ids=["unsupported", "missing", "empty", "wrong_case", "padded"],
    )
    async def test_should_reject_an_invalid_format_before_the_fetch(self, bad_format):
        # "PDF" and " pdf " are near-misses: the design declares parse
        # case-sensitive and unpadded, so a GREEN guard that .lower()/.strip()s
        # its input would silently widen the accepted set. Pinning them here
        # keeps the negative net a real discrimination proof, not a tautology.
        # The repository is empty, so a format that slipped past the guard would
        # return None, not raise. Raising proves the guard fired ahead of the
        # fetch -- a bad format is refused regardless of whether the id exists.
        with pytest.raises(ValidationException) as error:
            await ExportDocument(FakeDocumentRepository()).execute(
                document_id=uuid4(), owner_id=uuid4(), format=bad_format
            )

        assert error.value.error_code == "INVALID_FORMAT", (
            f"expected INVALID_FORMAT for {bad_format!r}, got {error.value.error_code}"
        )
        assert error.value.message == "The format must be pdf or docx.", (
            f"unexpected message for {bad_format!r}: {error.value.message}"
        )

    @pytest.mark.parametrize("good_format", ["pdf", "docx"])
    async def test_should_export_the_document_for_a_valid_format(self, good_format):
        owner_id = uuid4()
        document = stored_document(owner_id)

        found = await ExportDocument(await seeded(document)).execute(
            document_id=document.id, owner_id=owner_id, format=good_format
        )

        assert found is document, (
            f"a valid {good_format!r} export must proceed to the fetch and "
            "return the caller's own document, not be refused"
        )
