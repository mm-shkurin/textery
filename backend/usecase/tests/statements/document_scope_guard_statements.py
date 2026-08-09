from uuid import UUID

from document.document_scope import DocumentScope
from document.resolve_owned_document import resolve_owned_document
from shared.exceptions import NotFoundException
from statements.arranged import arranged
from statements.document_arrangement import DocumentArrangement
from statements.document_guard_contract import (
    ABSENT_DOCUMENT_ID,
    CALLER_ID,
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


class DocumentScopeGuardStatements(DocumentArrangement):
    """The shared document-scope guard the seven AI-edit usecases open with."""

    def __init__(self) -> None:
        super().__init__()
        self._foreign_refusal: NotFoundException | None = None
        self._absent_refusal: NotFoundException | None = None
        self._resolved_scope: DocumentScope | None = None

    def given_a_document_id_that_does_not_exist(self) -> None:
        # Nothing to seed: the id is absent precisely because no given_* step
        # writes it. Named as a step anyway so the scenario reads in full.
        pass

    async def resolve_the_foreign_document(self) -> None:
        self._foreign_refusal = await self._refusal_of(self.foreign_document_id)

    async def resolve_the_absent_document(self) -> None:
        self._absent_refusal = await self._refusal_of(ABSENT_DOCUMENT_ID)

    async def _refusal_of(self, document_id: UUID) -> NotFoundException:
        return await captured(
            self._resolve(document_id),
            NotFoundException,
            f"a refusal for document {document_id}",
        )

    async def resolve_the_callers_own_document(self) -> None:
        self._resolved_scope = await self._resolve(self.first_document_id)

    async def _resolve(self, document_id: UUID) -> DocumentScope:
        """The one place this family calls the guard, and so where the snapshot is taken.

        Lazily capturing the arranged versions here rather than in a `given_` step
        keeps every act step of this class covered by the version guard without any
        test having to remember it.
        """
        self.capture_the_versions_as_arranged(self.document_repository)
        return await resolve_owned_document(self.document_repository, document_id, CALLER_ID)

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
        own_id = self.first_document_id
        scope = arranged(self._resolved_scope, "resolved_scope")
        assert scope == DocumentScope(id=own_id, owner_id=CALLER_ID), (
            f"expected DocumentScope(id={own_id}, owner_id={CALLER_ID}), got {scope}"
        )
        assert_bounded_projection(
            scope, DOCUMENT_SCOPE_FIELD_NAMES, "content must never be materialised"
        )
