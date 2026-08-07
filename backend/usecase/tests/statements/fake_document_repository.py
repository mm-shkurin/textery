"""The in-memory DocumentRepository the usecase tests run against.

Its own module because `document_fakes` -- which also holds the document builders
and the three one-method doubles -- had grown past the 200-line limit, and this
class was most of it. `document_fakes` re-exports the name so the ten modules
importing it from there keep working; this file is where it is defined.
"""

from datetime import datetime
from uuid import UUID

from document.document import Document
from document.title_update import TitleUpdate
from shared.exceptions import ConflictException
from shared.keyset_cursor import KeysetCursor


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
        # BOTH unique constraints the real table carries. Mirroring only the
        # idempotency one would let the conversion's replay and race tests pass
        # against a storage that happily writes a second document for the same
        # generation -- the exact duplicate the constraint exists to prevent.
        # NULLs do not collide, matching Postgres: manual documents never contend.
        generation_clash = document.generation_id is not None and any(
            existing.generation_id == document.generation_id for existing in self.documents
        )
        if clash or generation_clash:
            raise ConflictException("document violates a uniqueness constraint")
        self.documents.append(document)

    async def find_by_generation_id(self, owner_id: UUID, generation_id: UUID) -> Document | None:
        return next(
            (
                d
                for d in self.documents
                if d.owner_id == owner_id and d.generation_id == generation_id
            ),
            None,
        )

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
        # All three intents, mirroring the real CAS. `erases()` is asked FIRST:
        # both `clear()` and `preserve()` carry no value, so a `carries_a_value()`
        # test alone maps them to the same "leave the title alone" and the clear
        # path reads green while doing nothing.
        if title.erases():
            stored.title = None
        elif title.carries_a_value():
            stored.title = title.value
        return stored


async def seeded(*documents: Document) -> FakeDocumentRepository:
    repository = FakeDocumentRepository()
    for document in documents:
        await repository.save_new(document)
    return repository
