"""Whole-entity comparison and the save boundary's content payloads.

Split out of `save_document_statements.py` only to keep that file under the
200-line cap; it is the same DSL.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from document.document import Document

# The content cap the save boundary enforces, with the payloads that sit either
# side of it. Owned here so the test classes never build an expected value from
# the same expression they submitted.
MAX_CONTENT = 200_000
CONTENT_AT_THE_MAXIMUM = "a" * MAX_CONTENT
CONTENT_PAST_THE_MAXIMUM = "a" * (MAX_CONTENT + 1)


@dataclass(frozen=True)
class DocumentState:
    """EVERY field of the entity, in one comparable value.

    Named per-field rather than compared as objects: `Document` has no
    `__eq__`, and the fake mutates and returns the SAME instance it stores, so
    `stored == saved` is an identity check that can never fail. A field-by-field
    record is the only comparison here that actually reads the values -- and it
    is what makes a partial "content and version match" assertion impossible to
    write by accident, so a save that quietly rewrote `title` or `updated_at`
    goes red.

    A frozen dataclass rather than a bare tuple so a failing comparison names
    the field that differs: a positional 10-tuple in an assertion message has
    to be counted out by hand to tell a `title` drift from an `updated_at` one.
    """

    id: UUID
    owner_id: UUID
    document_type: str
    status: str
    content: str
    version: int
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    title: str | None

    @classmethod
    def of(cls, document: Document) -> "DocumentState":
        return cls(
            id=document.id,
            owner_id=document.owner_id,
            document_type=document.document_type,
            status=document.status,
            content=document.content,
            version=document.version,
            idempotency_key=document.idempotency_key,
            created_at=document.created_at,
            updated_at=document.updated_at,
            title=document.title,
        )
