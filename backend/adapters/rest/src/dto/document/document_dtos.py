from datetime import datetime

from pydantic import BaseModel, StrictInt

from document.document import Document


class CreateDocumentRequestDto(BaseModel):
    # Only document_type. status/id/content sent by a client are dropped by
    # Pydantic's default extra="ignore" -- see
    # 05-manual-mode/decisions/server-owned-fields-ignored-decision.md. The enum is
    # NOT declared here: the domain's DocumentType owns it, so a bad value surfaces
    # as 422 {error_code: INVALID_DOCUMENT_TYPE} rather than Pydantic's envelope.
    document_type: str


class SaveDocumentRequestDto(BaseModel):
    content: str
    # StrictInt, not int: Pydantic v2's lax mode coerces "5" and 5.0 to 5, so a lax
    # `version: int` would silently ACCEPT two of the three shapes scenario 8.1
    # calls "non-integer". StrictInt also rejects JSON `true`, which would otherwise
    # arrive as 1 (bool subclasses int).
    version: StrictInt


class DocumentSummaryDto(BaseModel):
    """A document as it appears in the history list.

    Carries no `content`, deliberately -- and this is not a size micro-optimisation.
    documents_save.yaml caps content at 200,000 characters, so a 20-item page of
    full documents is a multi-megabyte response for a screen that renders titles.
    The editor fetches the one document it opens via GET /documents/{id}.
    """

    document_id: str
    document_type: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentSummaryDto":
        return cls(
            document_id=str(document.id),
            document_type=document.document_type,
            status=document.status,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class DocumentResponseDto(BaseModel):
    document_id: str
    document_type: str
    status: str
    content: str
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
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
