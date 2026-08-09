from statements.ai_edit_refusal_log_statements import AiEditRefusalLogStatements
from statements.ai_edit_scope_guard_statements import AiEditScopeGuardStatements
from statements.ai_edit_store_failure_statements import AiEditStoreFailureStatements


class TestAiEditScopeGuard:
    """An edit belonging to another document of the same owner is not found.

    Given an authenticated user owning two documents
    And an edit queued on the first document
    When the caller requests that edit under the second document's path
    Then the request is refused as not found

    At this layer the three edit-id-carrying endpoints (stream, state, cancel)
    share one resolver, so the guard is established once here rather than three
    times. The four tests after the scenario are the guards the hazard scan
    forced into the design: the ordering that keeps step 2 from being an
    unauthorized read, the outage that must not read as a 404, and the refusal
    record that makes a probe attributable on the server while staying
    indistinguishable to the caller.
    """

    async def test_should_refuse_an_edit_requested_under_another_document_of_the_same_owner(
        self, ai_edit_scope_guard_statements: AiEditScopeGuardStatements
    ):
        await ai_edit_scope_guard_statements.given_the_caller_owns_two_documents()
        ai_edit_scope_guard_statements.given_an_edit_queued_on_the_first_document()

        await ai_edit_scope_guard_statements.request_the_edit_under_the_second_document()
        await ai_edit_scope_guard_statements.request_the_edit_under_its_own_document()

        ai_edit_scope_guard_statements.assert_the_cross_document_refusal_is_canonical()
        ai_edit_scope_guard_statements.assert_the_edit_resolved_to_its_bounded_scope()
        ai_edit_scope_guard_statements.assert_the_arrangement_holds_the_minted_versions()
        ai_edit_scope_guard_statements.assert_no_document_gained_a_version()

    async def test_should_never_touch_the_edit_store_for_a_document_the_caller_cannot_resolve(
        self, ai_edit_scope_guard_statements: AiEditScopeGuardStatements
    ):
        await ai_edit_scope_guard_statements.given_the_caller_owns_two_documents()
        await ai_edit_scope_guard_statements.given_a_document_owned_by_another_account()
        ai_edit_scope_guard_statements.given_an_edit_queued_on_the_first_document()

        await ai_edit_scope_guard_statements.request_the_edit_under_the_foreign_document()
        await ai_edit_scope_guard_statements.request_the_edit_under_an_absent_document()

        ai_edit_scope_guard_statements.assert_the_edit_store_was_never_asked()

        await ai_edit_scope_guard_statements.request_the_edit_under_the_second_document()

        ai_edit_scope_guard_statements.assert_the_edit_store_was_asked_once_for_the_probed_document()
        ai_edit_scope_guard_statements.assert_the_arrangement_holds_the_minted_versions()
        ai_edit_scope_guard_statements.assert_no_document_gained_a_version()

    async def test_should_propagate_an_edit_store_outage_instead_of_refusing_as_not_found(
        self, ai_edit_store_failure_statements: AiEditStoreFailureStatements
    ):
        await ai_edit_store_failure_statements.given_the_caller_owns_two_documents()
        ai_edit_store_failure_statements.given_the_edit_store_is_unavailable()

        await ai_edit_store_failure_statements.request_the_edit_under_its_own_document()

        ai_edit_store_failure_statements.assert_the_outage_propagated_unchanged()
        ai_edit_store_failure_statements.assert_the_edit_store_was_asked_once()

    async def test_should_propagate_a_document_store_outage_instead_of_refusing_as_not_found(
        self, ai_edit_store_failure_statements: AiEditStoreFailureStatements
    ):
        await ai_edit_store_failure_statements.given_the_caller_owns_two_documents()

        await ai_edit_store_failure_statements.request_the_edit_while_the_document_store_is_down()

        ai_edit_store_failure_statements.assert_the_outage_propagated_unchanged()
        ai_edit_store_failure_statements.assert_the_edit_store_was_never_asked()

    async def test_should_record_the_two_refusals_under_distinct_causes_without_unresolved_ids(
        self, ai_edit_refusal_log_statements: AiEditRefusalLogStatements
    ):
        await ai_edit_refusal_log_statements.given_the_caller_owns_two_documents()
        ai_edit_refusal_log_statements.given_an_edit_queued_on_the_first_document()
        ai_edit_refusal_log_statements.given_the_guards_own_log_is_collected()

        await ai_edit_refusal_log_statements.request_the_edit_under_the_second_document()
        await ai_edit_refusal_log_statements.request_the_edit_under_an_absent_document()

        ai_edit_refusal_log_statements.assert_each_refusal_emitted_exactly_one_record()
        ai_edit_refusal_log_statements.assert_the_cross_document_record_omits_the_probed_id()
        ai_edit_refusal_log_statements.assert_the_absent_document_record_has_the_other_cause()
        ai_edit_refusal_log_statements.assert_the_two_causes_are_distinct()
