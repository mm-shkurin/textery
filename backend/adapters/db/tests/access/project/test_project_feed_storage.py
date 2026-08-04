import pytest


@pytest.mark.skip(
    reason="RED: SqlAlchemyProjectFeedRepository.list_feed raises NotImplementedError"
)
class TestProjectFeedRepositoryListFeed:
    """Scenario 1.1: the feed shows the caller's documents and nothing of anyone else's.

    Given two accounts, each holding one document written through the
    create-document usecase's storage port
    When each account's feed is read back through the feed read model
    Then each sees exactly their own row, and the port refuses an owner it was
    handed as None rather than reading unscoped.
    """

    async def test_should_return_the_callers_own_document(self, project_feed_statements):
        owner_id = await project_feed_statements.given_an_account()
        other_owner_id = await project_feed_statements.given_an_account()
        document = await project_feed_statements.given_a_document_written_by_its_owner(owner_id)
        await project_feed_statements.given_a_document_written_by_its_owner(other_owner_id)

        page = await project_feed_statements.list_feed(owner_id)

        project_feed_statements.assert_feed_holds_only(page, document)

    async def test_should_return_the_other_owners_document_to_that_owner_only(
        self, project_feed_statements
    ):
        # The mirror is not a duplicate: a query that ignored owner_id entirely
        # would still pass a single-owner assertion whenever the other account's
        # row happened to be filtered out for some unrelated reason.
        owner_id = await project_feed_statements.given_an_account()
        other_owner_id = await project_feed_statements.given_an_account()
        await project_feed_statements.given_a_document_written_by_its_owner(owner_id)
        other_document = await project_feed_statements.given_a_document_written_by_its_owner(
            other_owner_id
        )

        page = await project_feed_statements.list_feed(other_owner_id)

        project_feed_statements.assert_feed_holds_only(page, other_document)

    async def test_should_refuse_an_unresolved_owner_rather_than_reading_unscoped(
        self, project_feed_statements
    ):
        # The port's stated invariant, pinned where it can bite: SQLAlchemy compiles
        # `where(col == None)` to `IS NULL` rather than raising, so an implementation
        # that simply forwards the value serves a well-formed, empty 200 to a caller
        # whose identity was never established. Until now the guarantee existed only
        # as a Protocol docstring and an assert inside a test fake.
        await project_feed_statements.given_an_account()

        await project_feed_statements.assert_feed_refuses_an_unresolved_owner()
