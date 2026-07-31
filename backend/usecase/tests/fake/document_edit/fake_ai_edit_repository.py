from uuid import UUID

from document_edit.ai_edit_repository import AiEditRepository
from document_edit.ai_edit_scope import AiEditScope

from document.document_scope import DocumentScope
from statements.document_fakes import FakeDocumentRepository


class StorageUnavailableError(RuntimeError):
    """What a repository raises when the store is down or the query times out.

    Deliberately not one of our own domain exceptions: the point of the guard it
    proves is that whatever comes out of a repository travels to the caller
    unchanged, so the test uses an error the usecase layer has never heard of.
    """


class FakeAiEditRepository(AiEditRepository):
    """In-memory AiEditRepository that also spies on being called at all.

    Declared as an explicit subclass of the Protocol rather than relying on
    structural matching: a rename of the port's finder would otherwise leave every
    test here green against a fake that no longer resembles the thing it stands
    in for.

    The call log is not decoration: the ADR's first forced guard is that a
    document the caller cannot resolve never reaches the edit lookup, and a fake
    that only answers queries would let a guard doing the lookup first pass every
    other assertion in this file.

    Edits are seeded directly because story 19 has no queue usecase yet -- the
    scenario that creates them (§3) is implemented after this guard, per the
    read-before-write exception in the test-spec format rules. When
    `QueueAiEdit` lands, this seeding collapses into a call to it.
    """

    def __init__(self) -> None:
        self.edits: list[AiEditScope] = []
        self.lookups: list[tuple[UUID, UUID]] = []
        self.failure: Exception | None = None

    def seed_queued_edit(self, edit_id: UUID, document_id: UUID) -> None:
        self.edits.append(AiEditScope(id=edit_id, document_id=document_id))

    def fail_every_lookup_with(self, failure: Exception) -> None:
        self.failure = failure

    async def find_scope_by_id_and_document(
        self, edit_id: UUID, document_id: UUID
    ) -> AiEditScope | None:
        """Scoped by document, mirroring the real adapter's WHERE clause.

        A fake that matched on `edit_id` alone would answer the cross-document
        probe with the edit, and the scenario under test would go green against a
        storage that leaks.
        """
        self.lookups.append((edit_id, document_id))
        if self.failure is not None:
            raise self.failure
        return next(
            (e for e in self.edits if e.id == edit_id and e.document_id == document_id),
            None,
        )


class FailingDocumentScopeRepository(FakeDocumentRepository):
    """The ordinary document fake, with its scope lookup replaced by the outage.

    Built on `FakeDocumentRepository` rather than declared from scratch so the
    type checker holds it to the whole `DocumentRepository` port: a repository
    stub that satisfies only the one method the guard happens to call today would
    stop resembling the port the moment the port grew, and the outage test would
    keep passing against a shape no adapter could have.
    """

    def __init__(self, failure: Exception) -> None:
        super().__init__()
        self._failure = failure

    async def find_scope_by_id_and_owner(
        self, document_id: UUID, owner_id: UUID
    ) -> DocumentScope | None:
        raise self._failure
