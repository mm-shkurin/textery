from statements.refusal_record_shape_statements import RefusalRecordShapeStatements
from statements.revision_range_refusal_log_statements import RevisionRangeRefusalLogStatements
from statements.revision_refusal_log_statements import RevisionRefusalLogStatements
from statements.revision_silence_statements import RevisionSilenceStatements


class TestResolveOwnedRevisionRecords:
    """What the revision guard writes to its own log, for the same scenario.

    Split out of `TestResolveOwnedRevision` when that class outgrew the file-size
    limit. Same subject -- "a revision belonging to another document of the same
    owner is not found" -- seen from the server's side rather than the caller's:
    the refusal must be attributable to an account and a cause on the server while
    staying byte-identical to the caller, everything that is *not* a refusal must
    leave that channel empty, and the record must be built by the rule the edit
    guard uses rather than a second hand-written copy of it.
    """

    async def test_should_record_the_two_refusals_under_distinct_causes_without_unresolved_ids(
        self, revision_refusal_log_statements: RevisionRefusalLogStatements
    ):
        await revision_refusal_log_statements.given_the_caller_owns_two_documents()
        await revision_refusal_log_statements.given_a_revision_recorded_on_the_first_document()
        revision_refusal_log_statements.given_the_guards_own_log_is_collected()

        await revision_refusal_log_statements.request_the_revision_under_the_second_document()
        await revision_refusal_log_statements.request_the_revision_under_an_absent_document()

        revision_refusal_log_statements.assert_each_refusal_emitted_exactly_one_record()
        revision_refusal_log_statements.assert_the_cross_document_record_omits_the_probed_number()
        revision_refusal_log_statements.assert_the_absent_document_record_has_the_other_cause()
        revision_refusal_log_statements.assert_the_two_causes_are_distinct()
        revision_refusal_log_statements.assert_the_arrangement_holds_the_minted_versions()
        revision_refusal_log_statements.assert_no_document_gained_a_version()

    async def test_should_record_nothing_when_the_revision_resolves(
        self, revision_silence_statements: RevisionSilenceStatements
    ):
        await revision_silence_statements.given_the_caller_owns_two_documents()
        await revision_silence_statements.given_a_revision_recorded_on_the_first_document()
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

    async def test_should_record_an_unusable_revision_number_under_the_step_two_cause(
        self, revision_range_refusal_log_statements: RevisionRangeRefusalLogStatements
    ):
        await revision_range_refusal_log_statements.given_the_caller_owns_two_documents()
        revision_range_refusal_log_statements.given_the_guards_own_log_is_collected()

        await revision_range_refusal_log_statements.request_every_unusable_number_under_its_own_document()

        revision_range_refusal_log_statements.assert_every_unusable_number_was_the_canonical_refusal()
        revision_range_refusal_log_statements.assert_every_unusable_number_refused_at_step_two()
        revision_range_refusal_log_statements.assert_the_revision_store_was_never_asked()
        revision_range_refusal_log_statements.assert_the_arrangement_holds_the_minted_versions()
        revision_range_refusal_log_statements.assert_no_document_gained_a_version()

    async def test_should_still_attribute_an_unusable_number_aimed_at_an_unresolvable_document(
        self, revision_range_refusal_log_statements: RevisionRangeRefusalLogStatements
    ):
        await revision_range_refusal_log_statements.given_the_caller_owns_two_documents()
        await revision_range_refusal_log_statements.given_a_document_owned_by_another_account()
        revision_range_refusal_log_statements.given_the_guards_own_log_is_collected()

        await revision_range_refusal_log_statements.request_an_unusable_number_under_a_document_it_cannot_resolve()

        revision_range_refusal_log_statements.assert_every_unresolvable_probe_was_the_canonical_refusal()
        revision_range_refusal_log_statements.assert_an_unresolvable_document_still_records_the_attribution()
        revision_range_refusal_log_statements.assert_the_revision_store_was_never_asked()
        revision_range_refusal_log_statements.assert_the_arrangement_holds_the_minted_versions()
        revision_range_refusal_log_statements.assert_no_document_gained_a_version()

    async def test_should_build_its_refusal_record_by_the_same_rule_as_the_edit_guard(
        self, refusal_record_shape_statements: RefusalRecordShapeStatements
    ):
        await refusal_record_shape_statements.given_both_guards_are_arranged_and_collecting()

        await refusal_record_shape_statements.request_both_guards_refuse_at_both_steps()

        refusal_record_shape_statements.assert_both_guards_record_the_same_id_fields()
        refusal_record_shape_statements.assert_the_caller_is_attributable_at_both_steps()
        refusal_record_shape_statements.assert_neither_arrangement_gained_a_version()
