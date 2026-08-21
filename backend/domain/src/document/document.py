from datetime import datetime
from uuid import UUID, uuid4

from document.document_type import DocumentType
from document.idempotency_key import IdempotencyKey
from document.page_settings import PageSettings

DRAFT_STATUS = "draft"

# The status field's whole value space -- one member today. Not an allow-list a
# deployment may edit: adding a status is a domain change plus a migration, since
# the DB CHECK constraint is generated from this tuple.
DOCUMENT_STATUSES = (DRAFT_STATUS,)


class Document:
    """Domain entity for an editable document.

    `generation_id` is None for a manual document and set for one converted from
    a completed Generation (story 18). The field was deliberately ABSENT while
    manual mode was the only way in -- story 5's scenario 2.1 read "no generation
    is created or linked", and a missing column said that more strongly than a
    null. Story 18 made the link real: the auto path converts a generation into a
    document exactly once, and that "exactly once" is enforced by a UNIQUE
    constraint on this column, which needs the column to exist. A null still
    carries the original meaning -- nothing generated this document.

    **This entity deliberately does not increment its own version.** There is no
    `save_content()` doing `self.version += 1`, because an entity that owns the
    increment forces a read-compare-write storage -- exactly the shape that makes
    SqlAlchemyGenerationStorage.update() lose concurrent writes. The increment
    lives in a single SQL CAS statement instead (see SqlAlchemyDocumentStorage).
    The save path here is anemic on purpose: the invariant genuinely lives in the
    database, and modelling it in Python would only pretend otherwise.

    `page_settings` defaults to `None`, and `None` is "nobody has configured this
    document", NOT "configured to today's preset" -- the two must stay
    distinguishable all the way to the wire, so nothing here constructs a
    default. It is deliberately absent from `create`/`create_from_generation`:
    same mass-assignment guard shape as status/content/version.

    **`create_from_generation` is a sibling of `create`, not a parameter on it.**
    The two differ in what they are ALLOWED to accept, and collapsing them would
    hand the manual path a `content` argument it must never have. `create`'s
    empty content is the mass-assignment guard for manual documents (Security
    2.1) -- a client POSTing `content` to /documents cannot seed a document,
    because the signature has nowhere to put it. On the generation path content
    is server-derived: it is the sanitized conversion of text the model wrote,
    and the request body carries only a `generation_id`. `title` is likewise
    server-derived (see derive_generated_title) and `version` starts at 1 like
    any other draft -- the conversion is the document's first state, not an edit
    of one.

    **`reconstitute` is separate from `create`** because `create` hardcodes
    draft/empty/version=1: story 7 hit exactly this bug when AccountModel
    .to_domain used the constructor and read every account back unverified. A
    stored document must round-trip its real status, content and version, or
    every save would reset the CAS token to 1.
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
        title: str | None = None,
        generation_id: UUID | None = None,
        page_settings: PageSettings | None = None,
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
        self.title = title
        self.generation_id = generation_id
        self.page_settings = page_settings

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
    def create_from_generation(
        cls,
        owner_id: UUID,
        document_type: str,
        generation_id: UUID,
        content: str,
        title: str,
        idempotency_key: str,
        created_at: datetime,
    ) -> "Document":
        """Build the editable draft that a completed generation becomes.

        Why this is a sibling of `create` rather than an argument on it, and why
        `content` and `title` are accepted here only, is in the class docstring.
        """
        return cls(
            id=uuid4(),
            owner_id=owner_id,
            document_type=DocumentType(document_type).value,
            status=DRAFT_STATUS,
            content=content,
            version=1,
            idempotency_key=IdempotencyKey(idempotency_key).value,
            created_at=created_at,
            updated_at=created_at,
            title=title,
            generation_id=generation_id,
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
        title: str | None = None,
        generation_id: UUID | None = None,
        page_settings: PageSettings | None = None,
    ) -> "Document":
        """Rehydrate a stored document, preserving every persisted field (see class docstring)."""
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
            title=title,
            generation_id=generation_id,
            page_settings=page_settings,
        )
