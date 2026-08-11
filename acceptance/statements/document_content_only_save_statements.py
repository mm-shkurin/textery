from clients.application.dto.document.export_response_dto import ExportResponseDto
from clients.application.dto.document.save_document_response_dto import (
    SaveDocumentResponseDto,
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

# The status a draft document keeps across saves (ALLOWED_STATUSES is ("draft",)).
DRAFT_STATUS = "draft"
# The content-only save takes the document from 2 to 3. Named apart from the
# blank-title row's VERSION_AFTER_BLANK_SAVE despite sharing the value: the two rows
# submit DIFFERENT wire shapes (blank string vs. absent key) and nothing guarantees
# they stay arithmetically aligned -- a green that starts refusing one of them must
# fail on the row it broke, not silently follow a constant renamed for the other.
VERSION_AFTER_CONTENT_ONLY_SAVE = 3
# The body carried by the content-only autosave. DISTINCT from the setup save's
# DOCUMENT_CONTENT on purpose: with the same content resubmitted, a save that was
# refused or short-circuited is indistinguishable from one that landed. That
# distinctness is CASHED IN by `assert_content_only_save_preserved_the_title`, which
# pins this exact body on the save response -- without that pin the constant would be
# written to the wire and never observed.
CONTENT_ONLY_SAVE_CONTENT = "Тело, сохранённое без заголовка"
# The save response's `generation_id` for a manually created document: never converted
# from a generation, so null. Pinned rather than omitted so the full write shape is
# compared -- an omitted key is an unasserted key. That claim only became true when
# `assert_document_body` started comparing key sets for equality and reading values with
# `body[key]`: under the previous `body.get(key)` this null pin was satisfied just as
# well by the key VANISHING from the response, which is the one distinction -- absent
# vs. null -- this scenario exists to make.
MANUAL_DOCUMENT_GENERATION_ID = None


class DocumentContentOnlySaveStatements(DocumentExportFilenameStatements):
    """Scenario 2.1 statements — a content-only autosave (the title key omitted
    entirely) must leave the stored title alone.

    Sibling of DocumentBlankTitleSaveStatements, which covers scenario 3.2's other
    no-title-intent shape (a blank title sent BY VALUE). Kept in its own module for
    the same reason that file gives: neither may approach the 200-line cap.

    Subclasses DocumentExportFilenameStatements to reuse the shared cyrillic-title
    arrange (`_document_carrying_the_cyrillic_title`), the pdf export step and the
    filename assertion.
    """

    def __init__(self, client: ApplicationClient) -> None:
        super().__init__(client)
        # Filled by the content-only save. Its response is the DIRECT black-box view
        # of the surviving title (the PUT route returns DocumentResponseDto, which
        # carries `title`), so it is kept for a named assertion rather than discarded.
        self._document_id_after_content_only_save: str | None = None
        self._content_only_save: SaveDocumentResponseDto | None = None

    async def given_owner_autosaves_content_only_over_a_stored_title(
        self,
    ) -> ExportResponseDto:
        # The ABSENT-title row, and the only place in the repo where the absent-title
        # path runs in composition. Its two legs are each guarded alone and never
        # together: the router row drives {"content","version"} against a MOCKED
        # usecase, and the storage row hand-constructs TitleUpdate.preserve(). Neither
        # would go red if `title_update()` started reading absent-as-clear -- this row
        # is the one that would.
        #
        # `title=None` is not "send null": the client omits the key entirely in that
        # case, which is the distinction `model_fields_set` turns into preserve-vs-clear
        # and the shape a real frontend autosave puts on the wire.
        access_token, document_id = await self._document_carrying_the_cyrillic_title()
        content_only_save = await self._client.save_document(
            document_id=document_id,
            content=CONTENT_ONLY_SAVE_CONTENT,
            version=VERSION_AFTER_TITLE_SAVE,
            access_token=access_token,
            title=None,
        )
        # Kept, not asserted here: preserving a title by REFUSING the save would
        # satisfy the filename assertion, so the save response has to be pinned too --
        # but as a NAMED assertion the test class calls, not as a guard buried in an
        # arrange. `assert_content_only_save_preserved_the_title` does that work.
        self._document_id_after_content_only_save = document_id
        self._content_only_save = content_only_save
        return await self._export_as_pdf(document_id, access_token)

    def assert_content_only_save_preserved_the_title(self) -> None:
        # The DIRECT observation of the surviving title, and the reason this row does
        # not rest on the export header alone. PUT /documents/{id} returns
        # DocumentResponseDto, which carries `title` (document_dtos.py:108, populated
        # at :126) -- so the stored title is readable verbatim off the save's own
        # response, with no percent-encoding in the way.
        #
        # The whole write shape is compared, not just the title: a green that keeps the
        # title by refusing, short-circuiting, or partially applying the save fails
        # here. In particular `content` pins that CONTENT_ONLY_SAVE_CONTENT landed and
        # `version` pins that the CAS really incremented.
        body = body_of_successful_response(
            self._content_only_save, "content-only save"
        )
        expected = {
            "document_id": self._document_id_after_content_only_save,
            "document_type": SUPPORTED_DOCUMENT_TYPE,
            "status": DRAFT_STATUS,
            "content": CONTENT_ONLY_SAVE_CONTENT,
            "title": self.CYRILLIC_TITLE,
            "generation_id": MANUAL_DOCUMENT_GENERATION_ID,
            "version": VERSION_AFTER_CONTENT_ONLY_SAVE,
        }
        assert_document_body(body, expected, "content-only autosave")
