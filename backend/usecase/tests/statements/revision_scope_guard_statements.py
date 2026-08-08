from document_edit.revision_scope import RevisionScope

from statements.arranged import arranged
from statements.document_guard_contract import (
    ABSENT_DOCUMENT_ID,
    assert_bounded_projection,
    assert_is_the_canonical_refusal,
)
from statements.revision_guard_base import (
    RECORDED_REVISION_ID,
    RECORDED_REVISION_NUMBER,
    RevisionGuardBase,
)

# The bounded projection, pinned by literal name list rather than derived from
# `dataclasses.fields(RevisionScope)`: a guard derived from the thing it guards
# widens the moment the thing widens. A `content` field added later with a default
# would still satisfy dataclass equality, and the promise that the guard path never
# materialises up to 200 000 units of revision text would die without a red test.
#
# `id` is in the list on purpose, and it is the one entry that is not about size.
# `revision_number` is per-document, so a content loader keyed on the number alone
# is globally ambiguous -- it would copy another document's revision text into the
# caller's document, a cross-tenant leak that is also a write. The scope must carry
# the row id so no such loader is ever the cheapest thing to write.
#
# Qualified by scope name: 1.1 and 1.2 pin their own lists with deliberately
# different values, and same-named constants that must stay different are the drift
# trap the qualified names close.
REVISION_SCOPE_FIELD_NAMES = ["id", "revision_number", "document_id"]


class RevisionScopeGuardStatements(RevisionGuardBase):
    """The shared revision-scope guard the restore usecase opens with."""

    def __init__(self) -> None:
        super().__init__()
        self._cross_document_refusal: Exception | None = None
        self._absent_document_refusal: Exception | None = None
        self._foreign_document_refusal: Exception | None = None
        self._resolved_scope: RevisionScope | None = None

    async def request_the_revision_under_the_second_document(self) -> None:
        self._cross_document_refusal = await self.refusal_of(self.second_document_id)

    async def request_the_revision_under_its_own_document(self) -> None:
        self._resolved_scope = await self.resolve(self.first_document_id)

    async def request_the_revision_under_the_foreign_document(self) -> None:
        self._foreign_document_refusal = await self.refusal_of(self.foreign_document_id)

    async def request_the_revision_under_an_absent_document(self) -> None:
        self._absent_document_refusal = await self.refusal_of(ABSENT_DOCUMENT_ID)

    def assert_the_cross_document_refusal_is_canonical(self) -> None:
        """Type, byte-identical body and non-disclosure in one equality.

        Asserted against the literal rather than against the other refusal: that
        single equality settles all three properties at once -- the exact exception
        type, the body 1.1 fixed for all seven endpoints, and a body that provably
        carries neither the revision number nor the document id of a request whose
        whole premise is that the caller has no claim to that pair.
        """
        assert_is_the_canonical_refusal(
            arranged(self._cross_document_refusal, "cross_document_refusal"), "cross-document"
        )

    def assert_both_steps_refuse_identically(self) -> None:
        """Step 1 and step 2 are indistinguishable to the caller.

        Both pinned to the same imported literal, which settles the property
        absolutely: two refusals each equal to one shared expression of
        "canonical" are equal to each other, so a caller cannot tell them apart.

        A further `cross == absent` comparison used to sit below this, defended as
        catching a change that touched only one raise site. It could not: both
        operands had already been pinned by the *same* shared helper two lines
        above, so no implementation reaching that line could fail it. It was a
        tautology between two constants -- the shape this family keeps regrowing --
        and it is deliberately not written here. The mutual property is carried by
        the shared pin, not by a comparison that cannot go red.
        """
        assert_is_the_canonical_refusal(
            arranged(self._cross_document_refusal, "cross_document_refusal"), "cross-document"
        )
        assert_is_the_canonical_refusal(
            arranged(self._absent_document_refusal, "absent_document_refusal"), "absent-document"
        )

    def assert_the_foreign_document_refusal_is_canonical(self) -> None:
        """The other account's document, refused by the same one literal.

        The request step used to enforce this invisibly: `refusal_of` fails if
        nothing is raised, so the foreign-document probe carried a real contract --
        a `NotFoundException` and not a leak -- that no line of the test body
        showed. Recorded there, asserted here, where the reader can see it.
        """
        assert_is_the_canonical_refusal(
            arranged(self._foreign_document_refusal, "foreign_document_refusal"), "foreign-document"
        )

    def assert_the_revision_resolved_to_its_bounded_scope(self) -> None:
        """The positive control, plus the projection pinned by field name.

        Without the control, a guard that refused every request would satisfy the
        refusal assertion perfectly. The equality also pins the row `id`, which is
        the field a number-keyed content loader would not need and must have.
        """
        scope = arranged(self._resolved_scope, "resolved_scope")
        expected = RevisionScope(
            id=RECORDED_REVISION_ID,
            revision_number=RECORDED_REVISION_NUMBER,
            document_id=self.first_document_id,
        )
        assert scope == expected, f"expected {expected}, got {scope}"
        assert_bounded_projection(
            scope,
            REVISION_SCOPE_FIELD_NAMES,
            "no revision content, source or version may reach the guard path, and the row id "
            "must be there so no §7.x loader is ever keyed on the per-document number alone",
        )

    def assert_the_revision_store_was_never_asked(self) -> None:
        """The ordering guard: an unresolvable document never reaches step 2.

        Asserted as an exact empty call log rather than "the revision was not
        returned": a guard that looked the revision up first and only then checked
        the document would refuse identically and pass every other assertion in
        this file, while having already performed an unauthorized read.
        """
        self._assert_revision_lookups(
            [],
            "the revision lookup for a document the caller cannot resolve is itself an "
            "unauthorized read, so step 1 must refuse before step 2 runs",
        )

    def assert_the_revision_store_was_asked_once_for_the_probed_document(self) -> None:
        """The counterpart control: a resolvable document does reach step 2 exactly once."""
        self._assert_revision_lookups(
            [(RECORDED_REVISION_NUMBER, self.second_document_id)],
            "a document the caller does resolve must reach step 2, exactly once, scoped to the "
            "document that was probed and carrying the number as a parsed int",
        )
