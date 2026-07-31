from document_edit.ai_edit_scope import AiEditScope

from statements.ai_edit_guard_base import (
    AI_EDIT_SCOPE_FIELD_NAMES,
    QUEUED_EDIT_ID,
    AiEditGuardBase,
)
from statements.arranged import arranged
from statements.document_guard_contract import (
    ABSENT_DOCUMENT_ID,
    assert_bounded_projection,
    assert_is_the_canonical_refusal,
)


class AiEditScopeGuardStatements(AiEditGuardBase):
    """The shared edit-scope guard the three edit-id-carrying usecases open with."""

    def __init__(self) -> None:
        super().__init__()
        self._cross_document_refusal: Exception | None = None
        self._resolved_scope: AiEditScope | None = None

    async def request_the_edit_under_the_second_document(self) -> None:
        self._cross_document_refusal = await self.refusal_of(self.second_document_id)

    async def request_the_edit_under_its_own_document(self) -> None:
        self._resolved_scope = await self.resolve(self.first_document_id)

    async def request_the_edit_under_the_foreign_document(self) -> None:
        await self.refusal_of(self.foreign_document_id)

    async def request_the_edit_under_an_absent_document(self) -> None:
        await self.refusal_of(ABSENT_DOCUMENT_ID)

    def assert_the_cross_document_refusal_is_canonical(self) -> None:
        """Type, byte-identical body and non-disclosure in one equality.

        Asserted against the literal rather than against 1.1's refusal object:
        that single equality settles all three properties at once -- same exact
        exception type, the same body 1.1 fixed, and a body that provably carries
        neither the edit id nor the document id of a request whose whole premise
        is that the caller has no claim to that pair.
        """
        assert_is_the_canonical_refusal(
            arranged(self._cross_document_refusal, "cross_document_refusal"), "cross-document"
        )

    def assert_the_edit_resolved_to_its_bounded_scope(self) -> None:
        """The positive control, plus the projection pinned by field name.

        Without the control, a guard that refused every request would satisfy the
        refusal assertion perfectly. The field list is a literal, not
        `fields(AiEditScope)` -- deriving the expectation from the class under
        test is a guard that widens with the thing it guards, the lesson 1.1's
        red-adapter db step recorded.
        """
        scope = arranged(self._resolved_scope, "resolved_scope")
        expected = AiEditScope(id=QUEUED_EDIT_ID, document_id=self.first_document_id)
        assert scope == expected, f"expected {expected}, got {scope}"
        assert_bounded_projection(
            scope,
            AI_EDIT_SCOPE_FIELD_NAMES,
            "no instruction text, diff or generated content may reach the guard path",
        )

    def assert_the_edit_store_was_never_asked(self) -> None:
        """The ordering guard: an unresolvable document never reaches step 2.

        Asserted as an exact empty call log rather than "the edit was not
        returned": a guard that looked the edit up first and only then checked
        the document would refuse identically and pass every other assertion in
        this file, while having already performed an unauthorized read.
        """
        self.assert_edit_lookups(
            [],
            "the edit lookup for a document the caller cannot resolve is itself an "
            "unauthorized read, so step 1 must refuse before step 2 runs",
        )

    def assert_the_edit_store_was_asked_once_for_the_probed_document(self) -> None:
        """The counterpart control: a resolvable document does reach step 2 exactly once."""
        self.assert_edit_lookups(
            [(QUEUED_EDIT_ID, self.second_document_id)],
            "a document the caller does resolve must reach step 2, exactly once and "
            "scoped to the document that was probed",
        )
