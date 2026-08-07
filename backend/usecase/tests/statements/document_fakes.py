from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from document.document import Document
from document.page_settings import PageSettings

# Re-exported, not merely imported: `FakeDocumentRepository` moved to its own
# module for file size, not to be renamed, so the ten modules that import it
# from here must keep resolving. `seeded` travelled with it -- it builds one.
from statements.fake_document_repository import (  # noqa: F401
    FakeDocumentRepository,
    seeded,
)

# Public: tests that assert a stored document was NOT modified need a literal to
# compare against. Comparing `found.updated_at` to `document.updated_at` cannot
# work -- the fake repository hands back the very instance it was seeded with, so
# both sides of that comparison are the same attribute and a usecase that stamped
# the field would satisfy it.
STORED_AT = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)

_EPOCH = STORED_AT


def stored_document(
    owner_id: UUID, minutes_old: int = 0, content: str = "", title: str | None = None
) -> Document:
    """A persisted draft, `minutes_old` minutes older than the newest possible one.

    `title` drives the export-filename derivation (Sc 3.1) and is passed straight
    through the constructor now that the domain entity carries a `title` field.

    Deliberately says nothing about page settings: every document built here is one
    nobody has configured, which is exactly the state story 10 scenario 2.1 has to
    keep distinguishable from a configured one. The configured counterpart is
    `configured_document` below -- kept separate rather than added as a parameter
    here so that a factory whose page_settings argument stops being accepted breaks
    only the tests that are about page settings.
    """
    stored_at = _EPOCH - timedelta(minutes=minutes_old)
    return Document(
        id=uuid4(),
        owner_id=owner_id,
        document_type="эссе",
        status="draft",
        content=content,
        version=1,
        idempotency_key=f"key-{uuid4()}",
        created_at=stored_at,
        updated_at=stored_at,
        title=title,
    )


def configured_document(owner_id: UUID, page_settings: PageSettings) -> Document:
    """A persisted draft whose page geometry someone has actually set."""
    return Document(
        id=uuid4(),
        owner_id=owner_id,
        document_type="эссе",
        status="draft",
        content="<p>сохранено</p>",
        version=3,
        idempotency_key=f"key-{uuid4()}",
        created_at=_EPOCH,
        updated_at=_EPOCH,
        page_settings=page_settings,
    )


class FakeHtmlSanitizer:
    """Records what it was asked to clean and applies a visible marker.

    The marker matters: a sanitizer that returned its input unchanged would let a
    usecase that never calls it, or one that returns the raw request value instead
    of the stored one, pass every test.
    """

    def __init__(self) -> None:
        self.sanitized: list[str] = []

    def sanitize(self, content: str) -> str:
        self.sanitized.append(content)
        return content.replace("<script>", "").replace("</script>", "")


class FakeClock:
    def now(self) -> datetime:
        return _EPOCH


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commit_call_count = 0
        self.rollback_call_count = 0

    async def commit(self) -> None:
        self.commit_call_count += 1

    async def rollback(self) -> None:
        self.rollback_call_count += 1
