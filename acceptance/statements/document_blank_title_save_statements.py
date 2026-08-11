from clients.application.dto.document.export_response_dto import ExportResponseDto
from clients.application.dto.document.get_document_response_dto import (
    GetDocumentResponseDto,
)
from clients.application.application_client import ApplicationClient
from statements.document_body_assertions import (
    assert_document_body,
    body_of_successful_response,
)
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
# The read shape's eighth key. This document is created bare and never configured, and
# the read DTO carries absence as an explicit `page_settings: null` rather than by
# omitting the key or by substituting today's preset -- the confusion story 10 exists to
# prevent. Pinned to null, not merely tolerated: a save path that started defaulting a
# preset onto an unconfigured document would go red here.
PAGE_SETTINGS_NEVER_CONFIGURED = None


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
        # `page_settings` IS on this shape and is pinned below. It was previously
        # neither pinned nor mentioned, behind a comment claiming the timestamps were
        # "the only remaining response fields" -- the read DTO declares eight keys
        # (get_document_response_dto.py:60-67), and the tightened key-set equality in
        # `assert_document_body` is what turned that claim from plausible into red.
        #
        # That is a fact about the READ route only. It is NOT true that no endpoint
        # returns the title: the three write routes return DocumentResponseDto, which
        # does carry `title` (document_dtos.py:108, populated at :126) -- verified at
        # runtime, the PUT save response body carries all nine keys including it. So
        # title survival on this row is pinned by the companion
        # `assert_filename_rfc5987_encoded_from_title` step reading the export header,
        # and the sibling content-only row pins it directly off its save response.
        body = body_of_successful_response(
            self._reread_after_blank_save, "re-read after the blank-title save"
        )
        expected = {
            "document_id": self._document_id_after_blank_save,
            "document_type": SUPPORTED_DOCUMENT_TYPE,
            "status": DRAFT_STATUS,
            "content": BLANK_SAVE_CONTENT,
            "version": VERSION_AFTER_BLANK_SAVE,
            "page_settings": PAGE_SETTINGS_NEVER_CONFIGURED,
        }
        assert_document_body(body, expected, "blank-title autosave")
