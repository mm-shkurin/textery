from uuid import UUID

from document_edit.document_revision_repository import DocumentRevisionRepository
from document_edit.revision_scope import RevisionScope


class FakeDocumentRevisionRepository(DocumentRevisionRepository):
    """In-memory DocumentRevisionRepository that also spies on being called at all.

    Declared as an explicit subclass of the Protocol rather than relying on
    structural matching: a rename of the port's finder would otherwise leave every
    test here green against a fake that no longer resembles the thing it stands in
    for. (`FakeDocumentRepository` was left unbound in 1.1 and the review pass
    filed it; 1.2 bound its fake at birth, and so does this one.)

    The call log is not decoration. Two of this scenario's forced guards are
    counted rather than observed through the answer: a document the caller cannot
    resolve must never reach the revision lookup, and an out-of-range or
    non-integer number must be refused with the store asked **zero** times. A fake
    that only answered queries would let a guard that looks first and checks after
    pass every other assertion in this package.

    Revisions are seeded directly because story 19 has no apply/restore usecase
    yet -- a revision is only recorded when an AI edit applies (§7.2), which lands
    after this guard, per the read-before-write exception in the test-spec format
    rules. When that usecase exists, this seeding collapses into a call to it.
    """

    def __init__(self) -> None:
        self.revisions: list[RevisionScope] = []
        self.lookups: list[tuple[int, UUID]] = []
        self.failure: Exception | None = None

    def seed_revision(self, revision_id: UUID, revision_number: int, document_id: UUID) -> None:
        self.revisions.append(
            RevisionScope(id=revision_id, revision_number=revision_number, document_id=document_id)
        )

    def fail_every_lookup_with(self, failure: Exception) -> None:
        self.failure = failure

    async def find_scope_by_number_and_document(
        self, *, revision_number: int, document_id: UUID
    ) -> RevisionScope | None:
        """Scoped by document, mirroring the real adapter's WHERE clause.

        A fake that matched on `revision_number` alone would answer the
        cross-document probe with the first document's revision, and the scenario
        under test would go green against a storage that leaks.
        """
        self.lookups.append((revision_number, document_id))
        if self.failure is not None:
            raise self.failure
        return next(
            (
                revision
                for revision in self.revisions
                if revision.revision_number == revision_number
                and revision.document_id == document_id
            ),
            None,
        )
