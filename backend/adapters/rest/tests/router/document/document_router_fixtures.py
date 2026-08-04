from datetime import UTC, datetime
from uuid import UUID, uuid4

from document.document import Document

# The document's timestamps and the exact string the route must put on the wire
# for them. Kept as a matched pair, and the wire form is a hardcoded literal
# rather than `CREATED_AT.isoformat()`: a derived expectation would re-implement
# the serializer under test and pass for whatever format it happened to emit.
CREATED_AT = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
CREATED_AT_ON_THE_WIRE = "2026-07-17T12:00:00Z"


def a_document(owner_id: UUID, content: str = "", version: int = 1) -> Document:
    """A stored document owned by the account the Bearer override resolves to.

    The owner is a parameter, not a module constant read from `conftest`: three
    conftest modules sit on this suite's import path, so `from conftest import
    OWNER_ID` binds whichever one landed there first -- possibly a different
    constant than the fixture the client override actually uses. The generation
    slice's conftest documents that hazard; these files were doing it anyway.
    """
    return Document.reconstitute(
        id=uuid4(),
        owner_id=owner_id,
        document_type="эссе",
        status="draft",
        content=content,
        version=version,
        idempotency_key="key-1",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


def a_generated_document(owner_id: UUID, generation_id: UUID) -> Document:
    """A document that came from a generation, so `title` and `generation_id` are set.

    Both are non-null on purpose. The editor's documentFromGenerationApi.ts types
    them non-nullably, and an assertion that pinned them at None would still pass
    if the fields were dropped from the response shape and re-defaulted to None.
    """
    return Document.reconstitute(
        id=uuid4(),
        owner_id=owner_id,
        document_type="эссе",
        status="draft",
        content="<p>сгенерированный текст</p>",
        version=1,
        idempotency_key="gen-key-1",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        title="Влияние климата на урожайность",
        generation_id=generation_id,
    )
