import pytest


@pytest.mark.skip(
    reason="RED: no AI-edit db adapter at all -- ModuleNotFoundError: No module named "
    "'model.document_edit.ai_edit_model' (the four seeding cases) and "
    "'access.document_edit.ai_edit_storage' (the signature cases). GREEN adds the "
    "two-column ai_edits model, its migration, and "
    "SqlAlchemyAiEditStorage.find_scope_by_id_and_document."
)
class TestFindScopeByIdAndDocument:
    """Scenario 1.2: the bounded document-scoped existence check, against the real schema.

    The positive control is the point of this class, not an afterthought.
    `AiEditRepository` is a `Protocol` whose bodies `raise NotImplementedError`,
    which makes a *forgotten* method loud -- but the adapter will satisfy the port
    structurally, as `SqlAlchemyDocumentStorage` does, so that raise can never fire
    for it and only mypy sees a gap. Nothing but a real row read back through the
    real query proves the query resolves at all.

    **Both predicates are held down, and each by the case that can move without
    it.** The cross-document case seeds the edit under *another document of the
    same owner*, so a query filtering on `id` alone would resolve it and fail --
    and it is deliberately the same owner, because owner scoping is 1.1's job and
    would otherwise mask the missing `document_id` predicate. The absent-edit case
    asks under a document that *does* have edits, so a query filtering on
    `document_id` alone -- or a finder echoing its arguments back as a scope --
    would resolve something and fail. Asking under an empty document would have
    let both of those through.

    See 19-ai-chat-editing/decisions/edit-scope-guard-decision.md.
    """

    async def test_should_resolve_an_edit_of_its_own_document_to_its_scope(
        self, ai_edit_storage_statements
    ):
        (
            document_id,
            edit_id,
        ) = await ai_edit_storage_statements.given_a_document_with_a_queued_edit()

        scope = await ai_edit_storage_statements.find_scope(edit_id, document_id)

        ai_edit_storage_statements.assert_scope_matches(scope, edit_id, document_id)

    async def test_should_not_resolve_an_edit_of_another_document_of_the_same_owner(
        self, ai_edit_storage_statements
    ):
        statements = ai_edit_storage_statements
        (
            document_id,
            edit_id,
        ) = await statements.given_an_edit_under_another_document_of_the_same_owner()

        scope = await statements.find_scope(edit_id, document_id)

        statements.assert_an_edit_of_another_document_is_not_resolved(scope)

    async def test_should_not_resolve_an_absent_edit_under_a_document_that_has_edits(
        self, ai_edit_storage_statements
    ):
        document_id, _ = await ai_edit_storage_statements.given_a_document_with_a_queued_edit()

        scope = await ai_edit_storage_statements.find_scope_of_an_absent_edit(document_id)

        ai_edit_storage_statements.assert_an_absent_edit_is_not_resolved(scope)

    async def test_should_select_only_the_two_scope_columns(self, ai_edit_storage_statements):
        (
            document_id,
            edit_id,
        ) = await ai_edit_storage_statements.given_a_document_with_a_queued_edit()

        read = await ai_edit_storage_statements.find_scope_watching_what_it_reads(
            edit_id, document_id
        )

        ai_edit_storage_statements.assert_the_scope_was_resolved_reading_only_its_own_columns(
            read, edit_id, document_id
        )


@pytest.mark.skip(
    reason="RED: ModuleNotFoundError: No module named 'access.document_edit.ai_edit_storage'. "
    "GREEN adds SqlAlchemyAiEditStorage with a keyword-only find_scope_by_id_and_document."
)
class TestAiEditStorageShape:
    """The adapter's static obligations to its port -- no database involved.

    Separated from the behavioural class because these two need no session: they
    read a signature and an MRO off the shipped class.
    """

    def test_should_declare_both_scoping_ids_keyword_only(self, ai_edit_port_shape_statements):
        ai_edit_port_shape_statements.assert_the_scoping_ids_are_keyword_only()

    def test_should_satisfy_the_port_structurally(self, ai_edit_port_shape_statements):
        ai_edit_port_shape_statements.assert_the_storage_satisfies_the_port_structurally()
