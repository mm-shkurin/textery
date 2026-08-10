from clients.application.dto.document.export_response_dto import ExportResponseDto
from clients.application.dto.document.get_document_response_dto import (
    GetDocumentResponseDto,
)
from clients.application.application_client import ApplicationClient
from statements.document_export_filename_statements import (
    VERSION_AFTER_TITLE_SAVE,
    DocumentExportFilenameStatements,
)
from statements.document_export_statements import SUPPORTED_DOCUMENT_TYPE

# Each successful save is a CAS that increments: the title-bearing setup save takes
# the document from 1 to 2, the blank-title autosave from 2 to 3. Pinned as an exact
# literal rather than read back from the response -- an `isinstance(version, int)`
# check passes for a version the CAS never incremented, and threading the observed
# value forward would let a silently-added setup save go unnoticed.
VERSION_AFTER_BLANK_SAVE = 3
# The status a draft document keeps across saves (ALLOWED_STATUSES is ("draft",)).
DRAFT_STATUS = "draft"
# The body carried by the blank-title autosave. DISTINCT from DOCUMENT_CONTENT on
# purpose: the premise of that save is that it is a CONTENT-only autosave, so a green
# that rejects or short-circuits the whole blank-title request would lose the content
# update. With the same content resubmitted, that regression is indistinguishable from
# success; with a distinct body, the re-read pins that the save really landed.
BLANK_SAVE_CONTENT = "Обновлённое тело документа"


class DocumentBlankTitleSaveStatements(DocumentExportFilenameStatements):
    """Scenario 3.2 statements — a blank-title save must leave the stored title alone.

    Sibling of DocumentContentOnlySaveStatements, which covers scenario 2.1's other
    no-title-intent shape (the title key omitted entirely rather than sent blank).

    Subclasses DocumentExportFilenameStatements to reuse the shared cyrillic-title
    arrange (`_document_carrying_the_cyrillic_title`), the pdf export step and the
    filename assertion, and lives in its own module so neither file approaches the
    200-line cap. Nothing in the Scenario 3.1 filename-derivation concern calls back
    into this class.
    """

    def __init__(self, client: ApplicationClient) -> None:
        super().__init__(client)
        # Filled by the blank-title save so the persistence assertion can run as its
        # own named step rather than hiding inside the arrange.
        self._document_id_after_blank_save: str | None = None
        self._reread_after_blank_save: GetDocumentResponseDto | None = None

    async def given_owner_saves_a_blank_title_over_a_stored_title_and_exports(
        self, blank_title: str
    ) -> ExportResponseDto:
        # A client autosave that submits a blank title (empty or whitespace-only)
        # carries no title intent -- exactly like omitting the field. It must
        # therefore leave the previously stored title untouched, so the export
        # filename still reflects it.
        access_token, document_id = await self._document_carrying_the_cyrillic_title()
        blank_save = await self._client.save_document(
            document_id=document_id,
            content=BLANK_SAVE_CONTENT,
            version=VERSION_AFTER_TITLE_SAVE,
            access_token=access_token,
            title=blank_title,
        )
        self._assert_setup_save_succeeded(blank_save, "blank-title", VERSION_AFTER_BLANK_SAVE)
        self._document_id_after_blank_save = document_id
        self._reread_after_blank_save = await self._client.get_document(
            document_id=document_id, access_token=access_token
        )
        return await self._export_as_pdf(document_id, access_token)

    def assert_blank_title_save_persisted_the_document(self) -> None:
        # Preserving the title must not be achieved by refusing or ignoring the save:
        # the whole document the blank-title autosave left behind is pinned here, so a
        # save that was rejected, short-circuited, or only partially applied fails.
        #
        # The stored TITLE is absent from THIS comparison because it is absent from the
        # shape being compared: this is the GET re-read, and GetDocumentResponseDto --
        # the read shape, deliberately separate from the write shape -- declares no
        # title key (get_document_response_dto.py:60-67, and its docstring says so).
        #
        # That is a fact about the READ route only. It is NOT true that no endpoint
        # returns the title: the three write routes return DocumentResponseDto, which
        # does carry `title` (document_dtos.py:108, populated at :126) -- verified at
        # runtime, the PUT save response body carries all nine keys including it. So
        # title survival on this row is pinned by the companion
        # `assert_filename_rfc5987_encoded_from_title` step reading the export header,
        # and the sibling content-only row pins it directly off its save response.
        body = self._body_of_the_successful_reread()
        expected = {
            "document_id": self._document_id_after_blank_save,
            "document_type": SUPPORTED_DOCUMENT_TYPE,
            "status": DRAFT_STATUS,
            "content": BLANK_SAVE_CONTENT,
            "version": VERSION_AFTER_BLANK_SAVE,
        }
        assert {key: body.get(key) for key in expected} == expected, (
            f"expected the blank-title autosave to leave {expected!r}, got body={body!r}"
        )
        # created_at/updated_at are the only remaining response fields; their values are
        # wall-clock and so unpinnable, but their presence is not.
        assert {"created_at", "updated_at"} <= body.keys(), (
            f"expected the re-read to carry both timestamps, got body={body!r}"
        )

    def _body_of_the_successful_reread(self) -> dict:
        # The guard half of the persistence assertion: the arrange really ran, and the
        # post-save re-read really succeeded. Without both, `body` would fall back to
        # {} and every field pin below would compare None against its expectation --
        # failing for the wrong reason, or (for a future all-optional expectation)
        # passing vacuously.
        reread = self._reread_after_blank_save
        assert reread is not None, "arrange did not run: no re-read after the blank-title save"
        assert reread.status_code == 200, (
            f"expected the post-save re-read to succeed with 200, got "
            f"status_code={reread.status_code}, body={reread.body}"
        )
        return reread.body or {}
