from statements.arrangement_snapshot_guard_statements import ArrangementSnapshotGuardStatements


class TestArrangementSnapshotGuard:
    """The arrangement's refusal of a snapshot the act never used must itself be proven.

    Given an arrangement whose act was handed a document store it never seeded
    When the version assertions are called
    Then the post-act comparison refuses, and the arrangement comparison still holds

    `_refuse_a_snapshot_of_a_store_the_act_never_used` guards exactly one version
    assertion -- the post-act comparison -- and executed in no run before these
    tests, so it was mutation-proof by hand only. The last two tests are why it
    guards only that one: they call the *arrangement* comparison after the same
    foreign act and require it to hold, because it compares two values the act's
    choice of store cannot reach. A guard on both would refuse them.
    """

    async def test_should_refuse_a_post_act_version_comparison_when_the_act_used_a_foreign_store(
        self, arrangement_snapshot_guard_statements: ArrangementSnapshotGuardStatements
    ):
        statements = arrangement_snapshot_guard_statements
        await statements.given_the_caller_owns_two_documents()
        await statements.given_a_revision_recorded_on_the_first_document()

        await statements.act_on_a_store_outside_the_arrangement()

        statements.assert_the_foreign_act_reached_the_foreign_store()
        statements.assert_the_post_act_version_assertion_refuses()

    async def test_should_still_allow_the_arrangement_version_comparison_after_a_foreign_act(
        self, arrangement_snapshot_guard_statements: ArrangementSnapshotGuardStatements
    ):
        statements = arrangement_snapshot_guard_statements
        await statements.given_the_caller_owns_two_documents()
        await statements.given_a_revision_recorded_on_the_first_document()

        await statements.act_on_a_store_outside_the_arrangement()

        statements.assert_the_foreign_act_reached_the_foreign_store()
        statements.assert_the_arrangement_version_assertion_holds()

    async def test_should_keep_the_arrangement_comparison_after_an_own_act_then_a_foreign_one(
        self, arrangement_snapshot_guard_statements: ArrangementSnapshotGuardStatements
    ):
        statements = arrangement_snapshot_guard_statements
        await statements.given_the_caller_owns_two_documents()
        await statements.given_a_revision_recorded_on_the_first_document()

        await statements.act_on_the_arrangements_own_store()
        await statements.act_on_a_store_outside_the_arrangement()

        statements.assert_the_foreign_act_reached_the_foreign_store()
        statements.assert_the_arrangement_version_assertion_holds()
