from statements.document_scope_guard_statements import DocumentScopeGuardStatements


class TestDocumentScopeGuard:
    """Every endpoint refuses an absent document indistinguishably from a foreign one.

    Given an authenticated user
    And a document owned by another account
    When the caller invokes <endpoint> against it
    And the caller invokes <endpoint> against a document id that does not exist
    Then both are refused as not found
    And the two response bodies are byte-identical

    At this layer the seven endpoints share one resolver, so the identity is
    established once here rather than seven times: the byte-identical bodies the
    acceptance test asserts are the same refusal, rendered by the same handler.
    """

    async def test_should_refuse_a_foreign_document_exactly_as_an_absent_one(
        self, document_scope_guard_statements: DocumentScopeGuardStatements
    ):
        await document_scope_guard_statements.given_the_caller_owns_a_document()
        await document_scope_guard_statements.given_a_document_owned_by_another_account()
        document_scope_guard_statements.given_a_document_id_that_does_not_exist()

        await document_scope_guard_statements.resolve_the_foreign_document()
        await document_scope_guard_statements.resolve_the_absent_document()
        await document_scope_guard_statements.resolve_the_callers_own_document()

        # One canonical refusal, asserted against the literal rather than against
        # the other refusal: that single equality settles the exception type, the
        # byte-identical body, and the absence of any document id or instruction
        # text from the text the 404 handler logs verbatim.
        document_scope_guard_statements.assert_both_refusals_are_the_one_canonical_not_found()
        # The positive control: without it a guard that refused everything would
        # satisfy the identity assertion perfectly.
        document_scope_guard_statements.assert_the_own_document_resolved_to_its_scope()
