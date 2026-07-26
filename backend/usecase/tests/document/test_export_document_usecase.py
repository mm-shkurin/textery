"""ExportDocument: fetch-and-render side of exporting to PDF/DOCX.

Scenario 1.1 -- exporting a document id that does not exist is refused. The
usecase returns None (the refusal signal the router turns into a 404) rather
than raising, mirroring GetDocument: absent and foreign both collapse to None
because the repository filters on owner_id in SQL. A refused request must never
reach the render step -- the fake renderer stays untouched.

Scenario 1.3 -- an unsupported or missing format is refused. The format is
validated by `ExportFormat.parse` **before** the owner-scoped fetch, so a bad
format raises `ValidationException(INVALID_FORMAT)` regardless of whether the
target document exists -- and, again, never reaches render.

Scenario 2.1 -- a found document exports as a valid PDF. `execute` renders the
STORED content through the `DocumentRenderer` port under the parsed
`ExportFormat` and returns a result carrying the rendered bytes and the media
type `application/pdf`. Rendering the stored content (not the request, not the
raw entity) and pinning the exact sentinel bytes is the positive control: it
proves the render step ran on the caller's own content rather than being
tautologically refused.
"""

from uuid import uuid4

import pytest

from document.export_document import ExportDocument
from document.export_format import ExportFormat
from shared.exceptions import ValidationException
from statements.document_fakes import (
    FAKE_RENDERED_PDF,
    FakeDocumentRenderer,
    FakeDocumentRepository,
    seeded,
    stored_document,
)


@pytest.mark.skip(
    reason="RED: ExportDocument.__init__() takes no document_renderer arg / execute "
    "returns Document|None, not a rendered result (TypeError on construction)"
)
class TestExportDocument:
    async def test_should_answer_none_and_never_render_for_a_non_existent_document(self):
        renderer = FakeDocumentRenderer()

        found = await ExportDocument(
            document_repository=FakeDocumentRepository(), document_renderer=renderer
        ).execute(document_id=uuid4(), owner_id=uuid4(), format="pdf")

        assert found is None
        assert renderer.calls == [], "an absent document must never reach the render step"

    @pytest.mark.parametrize(
        "bad_format",
        ["xml", None, "", "PDF", " pdf "],
        ids=["unsupported", "missing", "empty", "wrong_case", "padded"],
    )
    async def test_should_reject_an_invalid_format_before_fetch_or_render(self, bad_format):
        # "PDF" and " pdf " are near-misses: the design declares parse
        # case-sensitive and unpadded, so a GREEN guard that .lower()/.strip()s
        # its input would silently widen the accepted set. The repository is
        # empty, so a format that slipped the guard would return None, not raise.
        # Raising -- with the renderer untouched -- proves the guard fired ahead
        # of both the fetch and the render: a bad format discloses nothing and
        # never drives a render.
        renderer = FakeDocumentRenderer()

        with pytest.raises(ValidationException) as error:
            await ExportDocument(
                document_repository=FakeDocumentRepository(), document_renderer=renderer
            ).execute(document_id=uuid4(), owner_id=uuid4(), format=bad_format)

        assert error.value.error_code == "INVALID_FORMAT", (
            f"expected INVALID_FORMAT for {bad_format!r}, got {error.value.error_code}"
        )
        assert error.value.message == "The format must be pdf or docx.", (
            f"unexpected message for {bad_format!r}: {error.value.message}"
        )
        assert renderer.calls == [], "a bad format must never reach the render step"

    async def test_should_render_the_stored_content_and_return_pdf_bytes(self):
        owner_id = uuid4()
        document = stored_document(owner_id, content="<p>Привет</p>")
        renderer = FakeDocumentRenderer()

        result = await ExportDocument(
            document_repository=await seeded(document), document_renderer=renderer
        ).execute(document_id=document.id, owner_id=owner_id, format="pdf")

        assert renderer.calls == [("<p>Привет</p>", ExportFormat.PDF)], (
            "the usecase must render the STORED content under the parsed pdf format"
        )
        assert result.content == FAKE_RENDERED_PDF
        assert result.media_type == "application/pdf"
