"""The guard on `DocumentArrangement`'s own guard.

`_refuse_a_snapshot_of_a_store_the_act_never_used` is real branching logic -- a
sticky latch set from `acted_on is not self.document_repository` and read by two
assertion methods -- and it has never executed in any run. The outage families do
set the latch, but none of them calls a version assertion, so the `assert` inside
it is dead in practice: dropping either call site, or weakening the `is not` to
`!=`, goes green and quietly returns those families to the vacuous-pass state the
latch was written to end.

That is the same defect as the one the forgotten-await gate exists for, one level
down: a guard nobody can drive red. So it is driven red here, from outside, by
arranging the very act it refuses.

The second claim is where the refusal *belongs*. Its justification is a
before/after comparison: `assert_no_document_gained_a_version` holds a snapshot
taken before the act and compares it against the store now, and if the act was
handed some other store then the snapshot describes rows the guard never touched.
`assert_the_arrangement_holds_the_minted_versions` makes no such comparison --
both of its sides (`_versions_as_arranged` and `_minted_versions`) are read off
`self.document_repository` and off the `given_` steps' literals, and neither can
be affected by which store the act was handed. Refusing it as well costs a valid
assertion, and because the latch is never reset it costs it for the rest of the
test: a test that acts on the arrangement and *then* on a failing store is told
to change its act in order to assert something that was never in doubt.

The choice pinned here is to **scope the refusal to the post-act assertion**
rather than to reset the latch per act. Resetting would make the refusal
order-dependent -- correct only if the version assertion is called before the next
act -- and the whole point of the lazy snapshot is that no test has to remember an
ordering.
"""

from collections.abc import Callable

from fake.document_edit.fake_ai_edit_repository import (
    FailingDocumentScopeRepository,
    StorageUnavailableError,
)
from statements.arranged import arranged
from statements.document_guard_contract import assert_is_the_store_outage, outcome_of
from statements.revision_guard_base import RevisionGuardBase

# The outage this family's foreign store raises. Named apart from the two the
# outage families use for the same reason those two are named apart from each
# other: same-named constants that must stay different are a drift trap.
FOREIGN_STORE_OUTAGE_MESSAGE = "the store this arrangement never seeded is down"

# Written out here rather than imported from `document_arrangement`: the subject
# under test is that module's guard, and importing its message would let any
# future edit to it approve itself. The remedy sentence is the load-bearing half
# -- a reader who meets this failure must be told it is test infrastructure
# talking, not a production defect.
EXPECTED_REFUSAL = (
    "the act was handed a document store other than this arrangement's, so the "
    "version snapshot describes rows the guard never touched -- the assertion would "
    "hold no matter what the guard did. Assert versions on a path that acts on "
    "`self.document_repository`, or teach the substitute to expose its rows"
)


class ArrangementSnapshotGuardStatements(RevisionGuardBase):
    """Drive the arrangement's snapshot refusal from a real foreign-store act."""

    def __init__(self) -> None:
        super().__init__()
        self._foreign_outcome: object | None = None

    async def act_on_the_arrangements_own_store(self) -> None:
        await self.resolve(self.first_document_id)

    async def act_on_a_store_outside_the_arrangement(self) -> None:
        """The outage families' act, taken for its side effect on the latch.

        Through `resolve_via` rather than by setting the flag directly: the claim
        is that a real act on a substitute store trips the refusal, and a test that
        reached in and set the latch would pass even if `capture_the_versions_as_
        arranged` stopped being called on that path at all.

        Records the outcome and judges none of it. Capturing through
        `captured_outage` here would enforce a behavioural contract -- that the
        foreign store's outage propagates -- from the act half, where no reader of
        the test body can see it, and would then throw the exception away.
        """
        failing = FailingDocumentScopeRepository(
            StorageUnavailableError(FOREIGN_STORE_OUTAGE_MESSAGE)
        )
        self._foreign_outcome = await outcome_of(self.resolve_via(failing, self.first_document_id))

    def assert_the_foreign_act_reached_the_foreign_store(self) -> None:
        """The precondition every other assertion in this family rests on.

        The latch is set by the act that was handed a substitute store. If the
        substitute were never reached -- a guard that short-circuits before the
        lookup, a `resolve_via` that quietly falls back to the arrangement's own
        repository -- the act would return normally, the latch would stay clear,
        and the refusal assertions below would be testing nothing at all.
        """
        assert_is_the_store_outage(
            arranged(self._foreign_outcome, "the foreign-store act's outcome"),
            FOREIGN_STORE_OUTAGE_MESSAGE,
            "the act on a store outside the arrangement",
        )

    def assert_the_post_act_version_assertion_refuses(self) -> None:
        """Type and whole message, not merely "it raised".

        A bare `pytest.raises(AssertionError)` here would be satisfied by the
        assertion failing for its *own* reason -- the store genuinely differing
        from the snapshot -- which is the outcome the refusal exists to replace.
        """
        self._assert_refuses(self.assert_no_document_gained_a_version)

    def assert_the_arrangement_version_assertion_holds(self) -> None:
        """The assertion that must survive the foreign act, because it is act-blind.

        Called for its absence of a raise, and the failure text names why it is
        allowed to run: both of its sides come off the arrangement's own store.
        """
        try:
            self.assert_the_arrangement_holds_the_minted_versions()
        except AssertionError as refused:
            raise AssertionError(
                f"the arrangement assertion refused with '{refused}', but it compares "
                f"`_versions_as_arranged` against `_minted_versions` -- both read off this "
                f"arrangement's own store and its given_ steps' literals, neither reachable "
                f"by whatever store the act was handed. Refusing it costs a valid assertion, "
                f"and the latch is never reset, so it costs it for the rest of the test"
            ) from refused

    def _assert_refuses(self, assertion: Callable[[], None]) -> None:
        try:
            assertion()
        except AssertionError as refused:
            actual = str(refused)
            assert actual == EXPECTED_REFUSAL, (
                f"the snapshot refusal read '{actual}', expected '{EXPECTED_REFUSAL}' -- the "
                f"message must name the test-infrastructure remedy, or the next reader "
                f"diagnoses it as a production defect"
            )
            return
        raise AssertionError(
            f"`{assertion.__name__}` compared a snapshot of a store the act never used and "
            f"passed. Its expectation was read off this arrangement's repository while the act "
            f"was handed another, so it holds no matter what the guard did to either"
        )
