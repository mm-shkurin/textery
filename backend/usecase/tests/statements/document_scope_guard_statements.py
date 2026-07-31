from uuid import UUID

from document.create_document import CreateDocument
from document.document_scope import DocumentScope
from document.resolve_owned_document import resolve_owned_document
from shared.exceptions import NotFoundException
from statements.arranged import arranged
from statements.document_fakes import FakeClock, FakeDocumentRepository
from statements.document_guard_contract import (
    ABSENT_DOCUMENT_ID,
    CALLER_ID,
    EPOCH,
    OTHER_ACCOUNT_ID,
    assert_bounded_projection,
    assert_is_the_canonical_refusal,
    captured,
)

# The bounded projection, pinned as a field list rather than only by equality: a
# `content` field added later with a default would still satisfy dataclass
# equality, and the guarantee that the guard never materialises the largest
# column in the schema would die silently.
#
# Qualified by scope name: 1.2 pins `AI_EDIT_SCOPE_FIELD_NAMES` with deliberately
# *different* values, and the two lists used to share the bare name
# `SCOPE_FIELD_NAMES` -- two same-named constants that must stay different is the
# drift trap the qualified names close.
DOCUMENT_SCOPE_FIELD_NAMES = ["id", "owner_id"]


class DocumentScopeGuardStatements:
    """The shared document-scope guard the seven AI-edit usecases open with."""

    def __init__(self) -> None:
        self._repository = FakeDocumentRepository()
        self._create_document = CreateDocument(self._repository, FakeClock(EPOCH))
        self._own_document_id: UUID | None = None
        self._foreign_document_id: UUID | None = None
        self._foreign_refusal: NotFoundException | None = None
        self._absent_refusal: NotFoundException | None = None
        self._resolved_scope: DocumentScope | None = None

    async def given_the_caller_owns_a_document(self) -> None:
        self._own_document_id = await self._seed(owner_id=CALLER_ID, key="key-own")

    async def given_a_document_owned_by_another_account(self) -> None:
        self._foreign_document_id = await self._seed(owner_id=OTHER_ACCOUNT_ID, key="key-foreign")

    def given_a_document_id_that_does_not_exist(self) -> None:
        # Nothing to seed: the id is absent precisely because no given_* step
        # writes it. Named as a step anyway so the scenario reads in full.
        pass

    async def _seed(self, owner_id: UUID, key: str) -> UUID:
        # Seeded through the real creation usecase rather than repository.save_new:
        # a hand-built row can hold a shape the application can never produce, and
        # the guard would then be proven against a document that cannot exist.
        result = await self._create_document.execute(
            owner_id=owner_id, document_type="эссе", idempotency_key=key
        )
        return result.document.id

    async def resolve_the_foreign_document(self) -> None:
        self._foreign_refusal = await self._refusal_of(
            arranged(self._foreign_document_id, "foreign_document_id")
        )

    async def resolve_the_absent_document(self) -> None:
        self._absent_refusal = await self._refusal_of(ABSENT_DOCUMENT_ID)

    async def _refusal_of(self, document_id: UUID) -> NotFoundException:
        return await captured(
            resolve_owned_document(self._repository, document_id, CALLER_ID),
            NotFoundException,
            f"a refusal for document {document_id}",
        )

    async def resolve_the_callers_own_document(self) -> None:
        self._resolved_scope = await resolve_owned_document(
            self._repository,
            arranged(self._own_document_id, "own_document_id"),
            CALLER_ID,
        )

    def assert_both_refusals_are_the_one_canonical_not_found(self) -> None:
        """Identity, non-disclosure and exception type in one equality each.

        Comparing the two refusals to each other would pass for a guard that
        raised an empty message for both, or one that leaked the same template
        with the id in it. Comparing each to the literal the ADR fixes settles all
        three properties: same exact type, byte-identical body, and a body that
        provably contains neither document id nor any instruction text.
        """
        assert_is_the_canonical_refusal(
            arranged(self._foreign_refusal, "foreign_refusal"), "foreign-document"
        )
        assert_is_the_canonical_refusal(
            arranged(self._absent_refusal, "absent_refusal"), "absent-document"
        )

    def assert_the_own_document_resolved_to_its_scope(self) -> None:
        own_id = arranged(self._own_document_id, "own_document_id")
        scope = arranged(self._resolved_scope, "resolved_scope")
        assert scope == DocumentScope(id=own_id, owner_id=CALLER_ID), (
            f"expected DocumentScope(id={own_id}, owner_id={CALLER_ID}), got {scope}"
        )
        assert_bounded_projection(
            scope, DOCUMENT_SCOPE_FIELD_NAMES, "content must never be materialised"
        )
