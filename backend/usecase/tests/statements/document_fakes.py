from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from document.document import Document
from document.title_update import TitleUpdate
from shared.exceptions import ConflictException
from shared.keyset_cursor import KeysetCursor

_EPOCH = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def stored_document(
    owner_id: UUID, minutes_old: int = 0, content: str = "", title: str | None = None
) -> Document:
    """A persisted draft, `minutes_old` minutes older than the newest possible one.

    `title` drives the export-filename derivation (Sc 3.1) and is passed straight
    through the constructor now that the domain entity carries a `title` field.
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


class FakeDocumentRepository:
    """In-memory DocumentRepository.

    Mirrors the real adapter's owner scoping rather than storing by id alone: a
    fake that ignores owner_id would let every ownership test pass against a
    storage that leaks. Story 7 learned this the hard way -- its fakes appended to
    a list, so an insert-only save() looked correct until /verify hit Postgres.
    """

    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.title_updates: list[TitleUpdate] = []

    async def save_new(self, document: Document) -> None:
        clash = any(
            existing.owner_id == document.owner_id
            and existing.idempotency_key == document.idempotency_key
            for existing in self.documents
        )
        if clash:
            raise ConflictException("document with this idempotency key already exists")
        self.documents.append(document)

    async def find_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> Document | None:
        return next(
            (d for d in self.documents if d.id == document_id and d.owner_id == owner_id),
            None,
        )

    async def find_by_idempotency_key(
        self, owner_id: UUID, idempotency_key: str
    ) -> Document | None:
        return next(
            (
                d
                for d in self.documents
                if d.owner_id == owner_id and d.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Document]:
        """Newest first, owner-scoped, anchored strictly after `cursor`.

        The ordering and the strict `<` are mirrored from the real adapter rather
        than simplified away: a fake that returned insertion order would let a
        usecase that forgot to trim the has-next probe row look correct, and a
        fake using `<=` would hide a cursor that re-serves its own anchor row.
        """
        rows = sorted(
            (d for d in self.documents if d.owner_id == owner_id),
            key=lambda d: (d.created_at, d.id),
            reverse=True,
        )
        if cursor is not None:
            rows = [d for d in rows if (d.created_at, d.id) < (cursor.created_at, cursor.id)]
        return rows[:limit]

    async def save_content_if_version_matches(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        expected_version: int,
        updated_at: datetime,
        *,
        title: TitleUpdate,
    ) -> Document | None:
        # REQUIRED, mirroring the port: the fake must not answer for the usecase.
        # A default here made an omitted argument indistinguishable from the
        # usecase forwarding `preserve()` itself. The sentinel that stood in for
        # this is gone with the port default it compensated for -- an omitted
        # argument is now a TypeError, which is a constraint rather than a
        # convention.
        # Recorded before the CAS guard so the intent the usecase forwarded is
        # observable regardless of whether the swap matched.
        self.title_updates.append(title)
        stored = await self.find_by_id_and_owner(document_id, owner_id)
        if stored is None or stored.version != expected_version:
            return None
        stored.content = content
        stored.version += 1
        stored.updated_at = updated_at
        # Preserve-on-`preserve()`, mirroring the real CAS: a title-less intent leaves the
        # existing title intact rather than wiping it.
        if title.carries_a_value():
            stored.title = title.value
        return stored


async def seeded(*documents: Document) -> FakeDocumentRepository:
    repository = FakeDocumentRepository()
    for document in documents:
        await repository.save_new(document)
    return repository


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
