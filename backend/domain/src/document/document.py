from datetime import datetime
from uuid import UUID, uuid4

from document.document_type import DocumentType
from document.idempotency_key import IdempotencyKey

DRAFT_STATUS = "draft"

ALLOWED_STATUSES = (DRAFT_STATUS,)


class Document:
    """Domain entity for a manually-authored (non-AI) document.

    No `generation_id`: a manual document has no Generation, and story #1 never
    built a Document to share a link field with -- scenario 2.1's "no generation
    is created or linked" is satisfied more strongly by the column's absence than
    by a null in it.

    **This entity deliberately does not increment its own version.** There is no
    `save_content()` doing `self.version += 1`, because an entity that owns the
    increment forces a read-compare-write storage -- exactly the shape that makes
    SqlAlchemyGenerationStorage.update() lose concurrent writes. The increment
    lives in a single SQL CAS statement instead (see SqlAlchemyDocumentStorage).
    The save path here is anemic on purpose: the invariant genuinely lives in the
    database, and modelling it in Python would only pretend otherwise.
    """

    def __init__(
        self,
        id: UUID,
        owner_id: UUID,
        document_type: str,
        status: str,
        content: str,
        version: int,
        idempotency_key: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.owner_id = owner_id
        self.document_type = document_type
        self.status = status
        self.content = content
        self.version = version
        self.idempotency_key = idempotency_key
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        owner_id: UUID,
        document_type: str,
        idempotency_key: str,
        created_at: datetime,
    ) -> "Document":
        """Build a new empty draft.

        `status`, `id`, `content`, and `version` are **not parameters**. That is
        the mass-assignment guard (Security 2.1 / scenario 1.2): a field the
        signature does not accept cannot be set by a client, which is stronger
        than a DTO that omits it or a filter that drops it -- neither of those
        binds a future caller.
        """
        return cls(
            id=uuid4(),
            owner_id=owner_id,
            document_type=DocumentType(document_type).value,
            status=DRAFT_STATUS,
            content="",
            version=1,
            idempotency_key=IdempotencyKey(idempotency_key).value,
            created_at=created_at,
            updated_at=created_at,
        )

    @classmethod
    def reconstitute(
        cls,
        id: UUID,
        owner_id: UUID,
        document_type: str,
        status: str,
        content: str,
        version: int,
        idempotency_key: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> "Document":
        """Rehydrate a stored document, preserving every persisted field.

        Separate from `create` because `create` hardcodes draft/empty/version=1:
        story 7 hit exactly this bug when AccountModel.to_domain used the
        constructor and read every account back unverified. A stored document
        must round-trip its real status, content and version, or every save
        would reset the CAS token to 1.
        """
        return cls(
            id=id,
            owner_id=owner_id,
            document_type=document_type,
            status=status,
            content=content,
            version=version,
            idempotency_key=idempotency_key,
            created_at=created_at,
            updated_at=updated_at,
        )
