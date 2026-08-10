"""The write no scope guard may take, and the two comparisons that would see one.

Split out of `document_arrangement`, which now holds only the arranging: the
documents a guard is pointed at, and the ids the tests name them by. Everything
about *versions* -- what the `given_` steps minted, what the store held at the
end of the arrangement, and what it holds after the act -- lives here, because
none of it reads an id and the arranging reads none of it.

The version guard is the part that was missing everywhere. Resolving a scope is a
read; "no new version is created" is a claim about a *write*, and no refusal
assertion in any of the three guard families could see one. A guard that refused
correctly and bumped -- or inserted -- a row on the way past satisfied every
assertion all three packages had.

Two separate statements, deliberately not one:

* `assert_the_arrangement_holds_the_minted_versions` compares the snapshot taken at
  the end of the arrangement against versions the `given_` steps named as literals.
  It fails when the *arrangement* is not a shape production can produce.
* `assert_no_document_gained_a_version` compares the store now against that
  snapshot. It fails when the *guard* wrote.

One whole-store equality against a per-test hardcoded mapping conflated the two:
adding a `given_` step to a test for an unrelated reason failed with text pointing
at production, and the cheapest diagnosis was to loosen back to enumerated ids --
reopening the very hole the whole-store form exists to close.
"""

from uuid import UUID

from statements.arranged import arranged
from statements.document_fakes import FakeDocumentRepository


class DocumentVersionLedger:
    """What the arrangement minted, what it left behind, and what the act did to it."""

    def __init__(self, document_repository: FakeDocumentRepository) -> None:
        self._document_repository = document_repository
        self._minted_versions: dict[UUID, int] = {}
        self._versions_as_arranged: dict[UUID, int] | None = None
        self._acted_on_a_store_outside_the_arrangement = False

    def record_the_minted_version(self, document_id: UUID, version: int) -> None:
        """What a `given_` step says it left behind, as a literal it named itself.

        Recorded by the arranging step rather than read back off the row it just
        wrote: an expectation sampled from the thing under observation agrees with
        whatever the guard did to it, including incrementing it.
        """
        self._minted_versions[document_id] = version

    def capture_the_versions_as_arranged(self, acted_on: object) -> None:
        """The end of the arrangement, taken at the first act rather than declared.

        Lazy and idempotent rather than an explicit `given_` step: a step would have
        to be remembered in every test of three packages, and the one test that
        forgot would be the one whose guard wrote.

        `acted_on` is the document store the act was actually handed, and it is a
        required argument for a reason. The outage families deliberately pass a
        *failing* repository into `resolve_via`, while the snapshot can only ever be
        read off the arrangement's own repository -- so a version assertion added to
        one of those tests would compare a store the guard never touched and pass no
        matter what the guard did. Harmless only for as long as nobody adds the
        assertion, which is exactly the kind of quiet the version guard exists to
        end: the whole claim of the lazy snapshot is that no test has to remember
        anything.

        The mismatch cannot be resolved by snapshotting the substitute (a failing
        double holds no rows at all), so it is recorded and made to fail loudly at
        the assertions instead of silently agreeing with itself.
        """
        if acted_on is not self._document_repository:
            self._acted_on_a_store_outside_the_arrangement = True
        if self._versions_as_arranged is None:
            self._versions_as_arranged = self._versions_now()

    def _refuse_a_snapshot_of_a_store_the_act_never_used(self) -> None:
        assert not self._acted_on_a_store_outside_the_arrangement, (
            "the act was handed a document store other than this arrangement's, so the "
            "version snapshot describes rows the guard never touched -- the assertion would "
            "hold no matter what the guard did. Assert versions on a path that acts on "
            "`self.document_repository`, or teach the substitute to expose its rows"
        )

    def assert_the_arrangement_holds_the_minted_versions(self) -> None:
        """The arranged store is the shape production produces, and nothing else.

        What this guards is the *versions*, and it guards them against literals:
        `_minted_versions` is filled by the arranging steps from their own constants,
        never read back off the row, so a creation that minted 5 or an applied edit
        that left the row at 1 fails here.

        What it does not guard is the roster. Every document in the arrangement is
        written by one `_seed`, which registers the same id on both sides of the
        equality, so a `given_` step that seeded a third document agrees with itself.
        That is an arrangement-authoring error, not a production write, and closing
        it would mean naming ids the creation usecase mints -- which the test cannot
        write as literals. `assert_no_document_gained_a_version` is the one that sees
        rows appear, because its expectation is a snapshot taken before the act.
        Both sides *here* read off the arrangement's own store and its `given_`
        literals, unreachable by the act's store -- which is why the snapshot
        refusal is scoped to that assertion rather than guarding this one too.
        """
        actual = arranged(self._versions_as_arranged, "versions_as_arranged")
        assert actual == self._minted_versions, (
            f"the arrangement left versions {actual}, expected {self._minted_versions} -- the "
            f"given_ steps must leave a store production could have produced, or the guard is "
            f"proven against documents that cannot exist"
        )

    def assert_no_document_gained_a_version(self) -> None:
        """The store after the act, against the snapshot taken before it.

        Compared against the snapshot rather than a mapping each test writes out:
        the hardcoded form was silently coupled to which `given_` steps ran, so a
        test that arranged one more document failed here, in production's words,
        for an arrangement reason.

        Compared whole for the same reason as above, and one further: a guard that
        *inserted* a row -- under the absent id it was handed, or under one it
        minted -- passes any aimed form of this assertion. The row set is inside
        the equality, so a version that moved and a row that appeared fail the same
        expression.
        """
        self._refuse_a_snapshot_of_a_store_the_act_never_used()
        expected = arranged(self._versions_as_arranged, "versions_as_arranged")
        actual = self._versions_now()
        assert actual == expected, (
            f"the store holds versions {actual}, expected {expected} as arranged -- resolving a "
            f"scope is a read, and a guard writing on the refusal path satisfies every other "
            f"assertion here while a document silently moves or appears"
        )

    def _versions_now(self) -> dict[UUID, int]:
        return {row.id: row.version for row in self._document_repository.documents}
