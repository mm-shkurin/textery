from clients.application.dto.document.export_response_dto import ExportResponseDto
from clients.application.dto.document.get_document_response_dto import (
    GetDocumentResponseDto,
)
from clients.application.dto.document.save_document_response_dto import (
    SaveDocumentResponseDto,
)
from clients.application.application_client import ApplicationClient
from statements.document_body_assertions import (
    assert_document_body,
    assert_save_advanced_the_update_stamp,
    body_of_successful_response,
)
from statements.document_export_filename_statements import (
    VERSION_AFTER_TITLE_SAVE,
    DocumentExportFilenameStatements,
)
from statements.document_export_statements import DRAFT_STATUS, SUPPORTED_DOCUMENT_TYPE

# Each successful save is a CAS that increments: the title-bearing setup save takes
# the document from 1 to 2, the blank-title autosave from 2 to 3. Pinned as an exact
# literal rather than read back from the response -- an `isinstance(version, int)`
# check passes for a version the CAS never incremented, and threading the observed
# value forward would let a silently-added setup save go unnoticed.
VERSION_AFTER_BLANK_SAVE = 3
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
# The write shape's `generation_id` for a manually created document: never converted
# from a generation, so null. Pinned rather than omitted for the reason the key-set
# equality in `assert_document_body` enforces -- an omitted key is an unasserted key,
# and `body[key]` makes this pin mean present-and-null rather than absent-or-null.
MANUAL_DOCUMENT_GENERATION_ID = None


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
        self._blank_save: SaveDocumentResponseDto | None = None
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
        # Kept, not asserted here. The blank-title save is this row's ACT, not its
        # arrange: guarding it with `_assert_setup_save_succeeded` reported a real
        # regression in the operation under test as `setup: ...`, i.e. as a broken
        # fixture. The sibling row states the same convention at
        # document_content_only_save_statements.py:83-86; the two now agree.
        self._blank_save = blank_save
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
        # `page_settings` IS on this shape and is pinned below: the read DTO declares
        # eight keys (get_document_response_dto.py:60-67), and key-set equality in
        # `assert_document_body` makes leaving any of them unnamed a red.
        #
        # The title's absence is a fact about the READ route only. The write routes
        # return DocumentResponseDto, which does carry `title` (document_dtos.py:108,
        # populated at :126) -- so the surviving title is pinned directly off this
        # row's own save response, below, rather than resting on the export header
        # that `assert_filename_rfc5987_encoded_from_title` reads.
        self._assert_the_save_returned_the_surviving_title()
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
        assert_save_advanced_the_update_stamp(body, "blank-title autosave")

    def _assert_the_save_returned_the_surviving_title(self) -> None:
        # The blank-title save's OWN response, previously observed only through an
        # arrange-phase guard that checked its status and version and dropped the other
        # seven keys. It is the write shape, so it carries the one field the re-read
        # cannot show: `title`, which must still be CYRILLIC_TITLE. Pinning the whole
        # shape here makes this row's central claim -- a blank title carries no title
        # intent -- observable on the response to the very request that made it.
        body = body_of_successful_response(self._blank_save, "blank-title save")
        expected = {
            "document_id": self._document_id_after_blank_save,
            "document_type": SUPPORTED_DOCUMENT_TYPE,
            "status": DRAFT_STATUS,
            "content": BLANK_SAVE_CONTENT,
            "title": self.CYRILLIC_TITLE,
            "generation_id": MANUAL_DOCUMENT_GENERATION_ID,
            "version": VERSION_AFTER_BLANK_SAVE,
        }
        assert_document_body(body, expected, "blank-title save response")
        assert_save_advanced_the_update_stamp(body, "blank-title save response")
