"""The keys every document-shaped response carries, declared once.

`DocumentSummaryDto`, `DocumentResponseDto` and `GetDocumentResponseDto` are three
genuinely different contracts -- the read shape has no `title`, the summary has no
`content` -- but all three repeat the same six identity/lifecycle keys and the same
six lines mapping them off the entity. Copied, they drift: a `version` that stops
being reported on one shape is a silent contract break the other two hide.
"""

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel

from document.document import Document


class DocumentIdentityFields(TypedDict):
    """The shared keys as keyword arguments, so `**` unpacking stays type-checked."""

    document_id: str
    document_type: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class DocumentIdentityDto(BaseModel):
    """The identity and lifecycle keys shared by every document response shape."""

    document_id: str
    document_type: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def identity_of(document: Document) -> DocumentIdentityFields:
        """The shared keys read off the entity, for a subclass's `from_domain`."""
        return DocumentIdentityFields(
            document_id=str(document.id),
            document_type=document.document_type,
            status=document.status,
            version=document.version,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
