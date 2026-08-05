from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, StrictInt

from document.document import Document
from document.title_update import TitleUpdate


class CreateDocumentRequestDto(BaseModel):
    # Only document_type. status/id/content sent by a client are dropped by
    # Pydantic's default extra="ignore" -- see
    # 05-manual-mode/decisions/server-owned-fields-ignored-decision.md. The enum is
    # NOT declared here: the domain's DocumentType owns it, so a bad value surfaces
    # as 422 {error_code: INVALID_DOCUMENT_TYPE} rather than Pydantic's envelope.
    document_type: str


class CreateDocumentFromGenerationRequestDto(BaseModel):
    """The conversion request body: one field, and it is an id the caller owns.

    Nothing else is accepted. `title`, `content`, `status`, `version` and even a
    spoofed `generation_id` on the response shape are server-derived, and
    Pydantic's default extra="ignore" drops them -- so a client cannot seed a
    document's text by POSTing it here. Same mass-assignment guard as
    CreateDocumentRequestDto, for the same reason.
    """

    generation_id: UUID


class SaveDocumentRequestDto(BaseModel):
    content: str
    # Optional with default None: a required title would 422 every current client
    # and autosave that saves content without a title. Plain str (not StrictStr) --
    # Pydantic v2 lax mode already rejects int/float/bool for a str field, so a
    # non-string title 422s without extra strictness. Scenario 3.1 forwards it to
    # SaveDocument.execute so the export filename can be derived from the title.
    title: str | None = None
    # StrictInt, not int: Pydantic v2's lax mode coerces "5" and 5.0 to 5, so a lax
    # `version: int` would silently ACCEPT two of the three shapes scenario 8.1
    # calls "non-integer". StrictInt also rejects JSON `true`, which would otherwise
    # arrive as 1 (bool subclasses int).
    version: StrictInt

    def title_update(self) -> TitleUpdate:
        """The wire's four rows onto the three-state intent (story 17's ADR): absent
        and ""/"   " preserve, null clears, a real title sets VERBATIM.

        Decided HERE -- absent and an explicit null both arrive as `title=None` and
        only `model_fields_set` tells them apart. No blank branch (`__post_init__`
        folds a blank given to `of()`; one routed into `clear()` skips that fold and
        wipes a title) and no `.strip()` -- `" Отчёт "` keeps its padding.
        """
        if "title" not in self.model_fields_set:
            return TitleUpdate.preserve()
        if self.title is None:
            return TitleUpdate.clear()
        return TitleUpdate.of(self.title)


class DocumentSummaryDto(BaseModel):
    """A document as it appears in the history list.

    Carries no `content`, deliberately -- and this is not a size micro-optimisation.
    documents_save.yaml caps content at 200,000 characters, so a 20-item page of
    full documents is a multi-megabyte response for a screen that renders titles.
    The editor fetches the one document it opens via GET /documents/{id}.

    It DOES carry `title`, and that is the fix for a real defect: without it the
    history list had nothing per-row but the document type and a date, so every
    доклад rendered as the same word and a user who had generated more than one
    could not tell which row was the report they wanted to keep editing. The
    title is already stored (CreateDocumentFromGeneration derives it from the
    generation's topic) -- it was simply not on this shape. Null for a manual
    document that has never been titled; the client falls back to the type label.
    """

    document_id: str
    document_type: str
    status: str
    title: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentSummaryDto":
        return cls(
            document_id=str(document.id),
            document_type=document.document_type,
            status=document.status,
            title=document.title,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class DocumentResponseDto(BaseModel):
    document_id: str
    document_type: str
    status: str
    content: str
    # Additive on the shape story 5 shipped (documents_from_generation.yaml says
    # so explicitly): null for a manual document, set for a converted one. Existing
    # consumers tolerate them because both are optional on the wire.
    title: str | None = None
    generation_id: str | None = None
    # Plain int: this is an output field built from the domain entity, never parsed
    # from client JSON, so there is no lax coercion to guard against here.
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentResponseDto":
        # Built from the entity the usecase returns, never from the request DTO.
        # That is what makes scenario 7.2 structural: the response cannot show
        # unsanitized content, because it never has access to it.
        return cls(
            document_id=str(document.id),
            document_type=document.document_type,
            status=document.status,
            content=document.content,
            title=document.title,
            generation_id=str(document.generation_id) if document.generation_id else None,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
