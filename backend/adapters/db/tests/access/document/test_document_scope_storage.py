class TestFindScopeByIdAndOwner:
    """Scenario 1.1: the bounded owner-scoped existence check, against the real schema.

    The positive control is the point of this class, not an afterthought.
    `DocumentRepository` is a `Protocol`, not an ABC: a storage that "implements"
    the port by inheriting from it inherits concrete method bodies. Those bodies
    now `raise NotImplementedError` -- they were `...`, which returns `None`, so
    the inheriting storage answered `None` for every input and refused every user
    their own documents while mypy and the whole usecase suite (which runs against
    the Fake) stayed green. The raise turns that into a loud failure, but only a
    real save read back through the real query proves the query itself resolves.

    The negative cases pin the guard's contract: a foreign document and an absent
    id must both fall out as `None` from the SQL predicate, so the usecase can
    raise one id-free refusal for both -- see
    19-ai-chat-editing/decisions/document-scope-guard-decision.md.

    **Both predicates are held down, and each by the case that can move without
    it.** The foreign-owner case seeds the document under someone else, so a query
    that filtered on `id` alone would resolve it and fail. The absent-id case
    seeds a document *for the asking owner* and then asks for a different id, so a
    query that filtered on `owner_id` alone -- or one that echoed its arguments
    back as a scope -- would resolve something and fail. Seeding no document there
    would have let both of those through: the owner would have had nothing to
    return either way.
    """

    async def test_should_resolve_the_owners_own_document_to_its_scope(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        await document_storage_statements.given_a_saved_document(owner_id)
        wanted = await document_storage_statements.given_a_saved_document(owner_id)

        scope = await document_storage_statements.find_scope_by_id_and_owner(wanted.id, owner_id)

        document_storage_statements.assert_scope_matches(scope, wanted)

    async def test_should_not_resolve_a_document_belonging_to_another_owner(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        other_owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        scope = await document_storage_statements.find_scope_by_id_and_owner(
            document.id, other_owner_id
        )

        document_storage_statements.assert_a_foreign_owners_document_is_not_resolved(scope)

    async def test_should_not_resolve_an_absent_id(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()
        await document_storage_statements.given_a_saved_document(owner_id)

        scope = await document_storage_statements.find_scope_of_an_absent_id(owner_id)

        document_storage_statements.assert_an_absent_id_is_not_resolved(scope)

    async def test_should_not_read_the_content_column(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        read = await document_storage_statements.find_scope_watching_what_it_reads(
            document.id, owner_id
        )

        document_storage_statements.assert_the_scope_was_resolved_without_reading_content(
            read, document
        )
