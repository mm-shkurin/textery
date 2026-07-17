from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID

from document.document import Document


class DocumentRepository(Protocol):
    """Port for document persistence.

    Every method takes `owner_id`. There is deliberately **no** `find_by_id`:
    ownership is enforced as a query predicate, so a foreign document falls out
    as `None` structurally and no caller can forget the check. An unscoped finder
    alongside these would be one autocomplete away from an IDOR -- see
    05-manual-mode/decisions/document-ownership-decision.md.
    """

    async def save_new(self, document: Document) -> None:
        """Insert a new document.

        Raises `ConflictException` when this owner has already used the
        idempotency key. That is the replay signal: the DB unique constraint
        decides, so there is no check-then-insert window.
        """
        ...

    async def find_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> Optional[Document]:
        ...

    async def find_by_idempotency_key(self, owner_id: UUID, idempotency_key: str) -> Optional[Document]:
        ...

    async def save_content_if_version_matches(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        expected_version: int,
        updated_at: datetime,
    ) -> Optional[Document]:
        """Compare-and-swap the content, returning the new state.

        Returns `None` when nothing matched -- which conflates "absent",
        "foreign", and "stale version" on purpose. The caller re-reads to tell
        them apart, and a foreign document must be indistinguishable from an
        absent one anyway.
        """
        ...
