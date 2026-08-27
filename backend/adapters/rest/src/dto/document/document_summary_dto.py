from document.document import Document
from dto.document.document_identity_dto import DocumentIdentityDto


class DocumentSummaryDto(DocumentIdentityDto):
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

    title: str | None = None

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentSummaryDto":
        return cls(**cls.identity_of(document), title=document.title)
