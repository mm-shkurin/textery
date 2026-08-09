from statements.revision_number_range_statements import RevisionNumberRangeStatements
from statements.revision_outage_statements import RevisionOutageStatements
from statements.revision_scope_guard_statements import RevisionScopeGuardStatements


class TestResolveOwnedRevision:
    """A revision belonging to another document of the same owner is not found.

    Given an authenticated user owning two documents
    And a revision recorded on the first document
    When the caller restores that revision number under the second document's path
    Then the request is refused as not found
    And no new version is created on either document

    At this layer the restore endpoint's scoping is one resolver, so the guard is
    established once here. The tests after the scenario are the guards the hazard
    scan forced into the design: the ordering that keeps step 2 from being an
    unauthorized read, the storage range Python ints do not have, the non-integer
    edge the route must not let FastAPI answer 422 for, the outages that must not
    read as 404s, and the refusal record that makes a probe attributable on the
    server while staying indistinguishable to the caller.
    """

    async def test_should_refuse_a_revision_requested_under_another_document_of_the_same_owner(
        self, revision_scope_guard_statements: RevisionScopeGuardStatements
    ):
        await revision_scope_guard_statements.given_the_caller_owns_two_documents()
        await revision_scope_guard_statements.given_a_revision_recorded_on_the_first_document()

        await revision_scope_guard_statements.request_the_revision_under_the_second_document()
        await revision_scope_guard_statements.request_the_revision_under_its_own_document()

        revision_scope_guard_statements.assert_the_cross_document_refusal_is_canonical()
        revision_scope_guard_statements.assert_the_revision_resolved_to_its_bounded_scope()
        revision_scope_guard_statements.assert_the_arrangement_holds_the_minted_versions()
        revision_scope_guard_statements.assert_no_document_gained_a_version()

    async def test_should_refuse_a_missing_document_and_a_missing_revision_identically(
        self, revision_scope_guard_statements: RevisionScopeGuardStatements
    ):
        await revision_scope_guard_statements.given_the_caller_owns_two_documents()
        await revision_scope_guard_statements.given_a_revision_recorded_on_the_first_document()

        await revision_scope_guard_statements.request_the_revision_under_the_second_document()
        await revision_scope_guard_statements.request_the_revision_under_an_absent_document()

        revision_scope_guard_statements.assert_both_steps_refuse_identically()
        revision_scope_guard_statements.assert_the_arrangement_holds_the_minted_versions()
        revision_scope_guard_statements.assert_no_document_gained_a_version()

    async def test_should_never_touch_the_revision_store_for_a_document_the_caller_cannot_resolve(
        self, revision_scope_guard_statements: RevisionScopeGuardStatements
    ):
        await revision_scope_guard_statements.given_the_caller_owns_two_documents()
        await revision_scope_guard_statements.given_a_document_owned_by_another_account()
        await revision_scope_guard_statements.given_a_revision_recorded_on_the_first_document()

        await revision_scope_guard_statements.request_the_revision_under_the_foreign_document()
        await revision_scope_guard_statements.request_the_revision_under_an_absent_document()

        revision_scope_guard_statements.assert_the_foreign_document_refusal_is_canonical()
        revision_scope_guard_statements.assert_the_revision_store_was_never_asked()

        await revision_scope_guard_statements.request_the_revision_under_the_second_document()

        revision_scope_guard_statements.assert_the_revision_store_was_asked_once_for_the_probed_document()
        revision_scope_guard_statements.assert_the_arrangement_holds_the_minted_versions()
        revision_scope_guard_statements.assert_no_document_gained_a_version()

    async def test_should_refuse_a_revision_number_outside_the_storage_range_without_asking(
        self, revision_number_range_statements: RevisionNumberRangeStatements
    ):
        await revision_number_range_statements.given_the_caller_owns_two_documents()

        await revision_number_range_statements.request_every_out_of_range_revision_number()

        revision_number_range_statements.assert_every_out_of_range_refusal_was_canonical()
        revision_number_range_statements.assert_the_store_was_never_asked()

    async def test_should_refuse_a_non_integer_revision_number_as_not_found_without_asking(
        self, revision_number_range_statements: RevisionNumberRangeStatements
    ):
        await revision_number_range_statements.given_the_caller_owns_two_documents()

        await revision_number_range_statements.request_every_non_integer_revision_number()

        revision_number_range_statements.assert_every_non_integer_refusal_was_canonical()
        revision_number_range_statements.assert_the_store_was_never_asked()

    async def test_should_carry_both_ends_of_the_storage_range_through_to_the_store(
        self, revision_number_range_statements: RevisionNumberRangeStatements
    ):
        await revision_number_range_statements.given_the_caller_owns_two_documents()

        await revision_number_range_statements.request_both_ends_of_the_valid_range()

        revision_number_range_statements.assert_both_ends_were_ordinary_misses()
        revision_number_range_statements.assert_both_ends_of_the_valid_range_reached_the_store()

    async def test_should_propagate_a_revision_store_outage_instead_of_refusing_as_not_found(
        self, revision_outage_statements: RevisionOutageStatements
    ):
        await revision_outage_statements.given_the_caller_owns_two_documents()
        revision_outage_statements.given_the_revision_store_is_unavailable()

        await revision_outage_statements.request_the_revision_under_its_own_document()

        revision_outage_statements.assert_the_outage_propagated_unchanged()
        revision_outage_statements.assert_the_revision_store_was_asked_once()

    async def test_should_propagate_a_document_store_outage_instead_of_refusing_as_not_found(
        self, revision_outage_statements: RevisionOutageStatements
    ):
        await revision_outage_statements.given_the_caller_owns_two_documents()

        await revision_outage_statements.request_the_revision_while_the_document_store_is_down()

        revision_outage_statements.assert_the_outage_propagated_unchanged()
        revision_outage_statements.assert_the_revision_store_was_never_asked()
