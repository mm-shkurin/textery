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

Scenario 2.2 -- a found document exports as a valid DOCX. The docx positive
control mirrors 2.1 but pins the Word media type
`application/vnd.openxmlformats-officedocument.wordprocessingml.document`. Its
companion is an exhaustiveness guard: EVERY `ExportFormat` member must resolve
to a media type in the usecase's `_MEDIA_TYPE` map, so a future format added
without a media type fails loudly here at import-check time rather than 500-ing
at runtime the first time a caller requests it. Fail-fast ordering (media lookup
before render) is deliberately NOT tested: with only pdf/docx and both mapped
after GREEN, no parseable-but-unmapped format exists, so the ordering is
un-observable via the public API and contriving an invalid enum member is
forbidden -- tests 2.2 + the exhaustiveness guard cover the invariant.
"""

import pytest

from document.export_format import ExportFormat
from statements.export_document_statements import ExportStatements

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def statements():
    return ExportStatements()


class TestExportDocument:
    async def test_should_answer_none_and_never_render_for_a_non_existent_document(
        self, statements
    ):
        statements.given_no_stored_document()

        await statements.when_exporting("pdf")

        statements.assert_export_withheld()
        statements.assert_nothing_was_rendered()

    @pytest.mark.parametrize(
        "bad_format",
        ["xml", None, "", "PDF", " pdf "],
        ids=["unsupported", "missing", "empty", "wrong_case", "padded"],
    )
    async def test_should_reject_an_invalid_format_before_fetch_or_render(
        self, statements, bad_format
    ):
        # "PDF" and " pdf " are near-misses: the design declares parse
        # case-sensitive and unpadded, so a GREEN guard that .lower()/.strip()s
        # its input would silently widen the accepted set. The repository is
        # empty, so a format that slipped the guard would return None, not raise.
        # Raising -- with the renderer untouched -- proves the guard fired ahead
        # of both the fetch and the render: a bad format discloses nothing and
        # never drives a render.
        statements.given_no_stored_document()

        await statements.when_exporting_is_refused(bad_format)

        statements.assert_invalid_format_reported(bad_format)
        statements.assert_nothing_was_rendered()

    async def test_should_render_the_stored_content_and_return_pdf_bytes(self, statements):
        await statements.given_a_stored_document(content="<p>Привет</p>")

        await statements.when_exporting("pdf")

        statements.assert_rendered_stored_content("<p>Привет</p>", ExportFormat.PDF)
        statements.assert_export_is(media_type=PDF_MEDIA_TYPE, filename="document.pdf")

    async def test_should_render_the_stored_content_and_return_docx_bytes(self, statements):
        await statements.given_a_stored_document(content="<p>Пока</p>")

        await statements.when_exporting("docx")

        statements.assert_rendered_stored_content("<p>Пока</p>", ExportFormat.DOCX)
        statements.assert_export_is(media_type=DOCX_MEDIA_TYPE, filename="document.docx")

    @pytest.mark.parametrize(
        "title, export_format, expected_media_type, expected_filename",
        [
            ("Привет Мир", "pdf", PDF_MEDIA_TYPE, "Привет Мир.pdf"),
            ("Привет Мир", "docx", DOCX_MEDIA_TYPE, "Привет Мир.docx"),
            (None, "pdf", PDF_MEDIA_TYPE, "document.pdf"),
            ("   ", "pdf", PDF_MEDIA_TYPE, "document.pdf"),
            (" Отчёт ", "pdf", PDF_MEDIA_TYPE, "Отчёт.pdf"),
        ],
        ids=[
            "cyrillic_title_pdf",
            "cyrillic_title_docx",
            "absent_title_default",
            "whitespace_title_default",
            "padded_title_stripped",
        ],
    )
    async def test_should_derive_the_plain_filename_from_the_title(
        self, statements, title, export_format, expected_media_type, expected_filename
    ):
        # Derivation is a usecase policy: the filename stem is the title when
        # present, else the default "document"; the extension follows the format
        # (.pdf/.docx), closing the Sc 2.2 hardcoded-document.pdf carry-forward.
        # The filename is the PLAIN unicode string -- RFC 5987 percent-encoding is
        # an HTTP wire concern owned by the rest adapter, NOT tested here.
        # `whitespace_title_default` is DEFENSE IN DEPTH, not a duplicate of the
        # save-boundary blank rule (Sc 3.2): the save boundary governs only writes
        # made THROUGH it, while rows written before that green (today's
        # `SET title = ''` is live) or by a migration/import/admin tool bypass it
        # entirely and would otherwise derive `%20%20%20.pdf` forever. Derivation
        # is where "never empty" is enforceable for every input.
        # `padded_title_stripped` guards the INTERSECTION the other cases leave
        # open: `padded_title_verbatim` pins that " Отчёт " is STORED verbatim and
        # `whitespace_title_default` pins only the all-blank case, so a derivation
        # that TESTS blankness (`title if title.strip() else "document"`) rather
        # than STRIPPING satisfies both and still ships " Отчёт .pdf". The ADR's
        # rule is `stem = (title or "").strip() or "document"` -- strip for the
        # FILENAME, never for the stored title.
        await statements.given_a_stored_document(content="<p>Привет</p>", title=title)

        await statements.when_exporting(export_format)

        # The whole export envelope, not just the filename: the media type and the
        # rendered bytes are deterministic on every one of these params, so pinning
        # only the stem would let either regress unnoticed across all five.
        statements.assert_export_is(media_type=expected_media_type, filename=expected_filename)
        # The other half of the ADR sentence: the strip belongs to the FILENAME,
        # never to the stored entity. Asserted for every param, since the invariant
        # is not specific to the padded case -- but it is the padded one it makes
        # load-bearing, because there a green is tempted to normalise the entity
        # (or the mapper) instead of the derived stem.
        await statements.assert_stored_document_unchanged(title)

    def test_every_export_format_resolves_to_a_media_type(self, statements):
        # Structural invariant, not a transient state: it stays green for any
        # future format once that format is mapped, and fails loudly the moment a
        # member is added without a media type -- the loud failure the moved
        # media lookup (ADR) turns from a runtime 500 into an import-time guard.
        statements.assert_every_export_format_resolves_to_a_media_type()
