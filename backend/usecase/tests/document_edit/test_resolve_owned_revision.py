import pytest

from statements.refusal_record_shape_statements import RefusalRecordShapeStatements
from statements.revision_number_range_statements import RevisionNumberRangeStatements
from statements.revision_outage_statements import RevisionOutageStatements
from statements.revision_refusal_log_statements import RevisionRefusalLogStatements
from statements.revision_scope_guard_statements import RevisionScopeGuardStatements
from statements.revision_silence_statements import RevisionSilenceStatements


@pytest.mark.skip(
    reason="RED: resolve_owned_revision is a stub -- 8 tests raise NotImplementedError out of "
    "the guard, and 4 fail with AssertionError, each naming NotImplementedError('') where the "
    "contract was expected: the two outage tests expect "
    "StorageUnavailableError('document_revisions read timed out'), the either-store-down test "
    "expects StorageUnavailableError('the store is down'), and the storage-range test expects "
    "NotFoundException('document not found') for the in-range boundary. 12 failed, 0 passed."
)
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
        revision_scope_guard_statements.given_a_revision_recorded_on_the_first_document()

        await revision_scope_guard_statements.request_the_revision_under_the_second_document()
        await revision_scope_guard_statements.request_the_revision_under_its_own_document()

        revision_scope_guard_statements.assert_the_cross_document_refusal_is_canonical()
        revision_scope_guard_statements.assert_the_revision_resolved_to_its_bounded_scope()
        revision_scope_guard_statements.assert_neither_document_gained_a_version()

    async def test_should_refuse_a_missing_document_and_a_missing_revision_identically(
        self, revision_scope_guard_statements: RevisionScopeGuardStatements
    ):
        await revision_scope_guard_statements.given_the_caller_owns_two_documents()
        revision_scope_guard_statements.given_a_revision_recorded_on_the_first_document()

        await revision_scope_guard_statements.request_the_revision_under_the_second_document()
        await revision_scope_guard_statements.request_the_revision_under_an_absent_document()

        revision_scope_guard_statements.assert_both_steps_refuse_identically()

    async def test_should_never_touch_the_revision_store_for_a_document_the_caller_cannot_resolve(
        self, revision_scope_guard_statements: RevisionScopeGuardStatements
    ):
        await revision_scope_guard_statements.given_the_caller_owns_two_documents()
        await revision_scope_guard_statements.given_a_document_owned_by_another_account()
        revision_scope_guard_statements.given_a_revision_recorded_on_the_first_document()

        await revision_scope_guard_statements.request_the_revision_under_the_foreign_document()
        await revision_scope_guard_statements.request_the_revision_under_an_absent_document()

        revision_scope_guard_statements.assert_the_foreign_document_refusal_is_canonical()
        revision_scope_guard_statements.assert_the_revision_store_was_never_asked()

        await revision_scope_guard_statements.request_the_revision_under_the_second_document()

        revision_scope_guard_statements.assert_the_revision_store_was_asked_once_for_the_probed_document()

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

    async def test_should_record_the_two_refusals_under_distinct_causes_without_unresolved_ids(
        self, revision_refusal_log_statements: RevisionRefusalLogStatements
    ):
        await revision_refusal_log_statements.given_the_caller_owns_two_documents()
        revision_refusal_log_statements.given_a_revision_recorded_on_the_first_document()
        revision_refusal_log_statements.given_the_guards_own_log_is_collected()

        await revision_refusal_log_statements.request_the_revision_under_the_second_document()
        await revision_refusal_log_statements.request_the_revision_under_an_absent_document()

        revision_refusal_log_statements.assert_each_refusal_emitted_exactly_one_record()
        revision_refusal_log_statements.assert_the_cross_document_record_omits_the_probed_number()
        revision_refusal_log_statements.assert_the_absent_document_record_has_the_other_cause()
        revision_refusal_log_statements.assert_the_two_causes_are_distinct()

    async def test_should_record_nothing_when_the_revision_resolves(
        self, revision_silence_statements: RevisionSilenceStatements
    ):
        await revision_silence_statements.given_the_caller_owns_two_documents()
        revision_silence_statements.given_a_revision_recorded_on_the_first_document()
        revision_silence_statements.given_the_guards_own_log_is_collected()

        await revision_silence_statements.request_the_revision_under_its_own_document()

        revision_silence_statements.assert_the_revision_actually_resolved()
        revision_silence_statements.assert_the_successful_resolution_was_silent()

    async def test_should_record_nothing_when_either_store_is_down(
        self, revision_silence_statements: RevisionSilenceStatements
    ):
        await revision_silence_statements.given_the_caller_owns_two_documents()
        revision_silence_statements.given_the_guards_own_log_is_collected()

        await revision_silence_statements.request_the_revision_while_either_store_is_down()

        revision_silence_statements.assert_each_outage_reached_the_caller()
        revision_silence_statements.assert_both_outages_were_silent()

    async def test_should_build_its_refusal_record_by_the_same_rule_as_the_edit_guard(
        self, refusal_record_shape_statements: RefusalRecordShapeStatements
    ):
        await refusal_record_shape_statements.given_both_guards_have_refused_at_both_steps()

        refusal_record_shape_statements.assert_both_guards_record_the_same_id_fields()
        refusal_record_shape_statements.assert_the_caller_is_attributable_at_both_steps()
