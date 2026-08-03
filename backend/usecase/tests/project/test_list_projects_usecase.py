class TestProjectFeedIsOwnerScoped:
    """Scenario 1.1: The feed shows the caller's documents and nothing of anyone else's.

    Given an authenticated user with documents
    And another account with its own documents
    When they request their projects
    Then only their own documents are returned
    And the other account's documents are absent.
    """

    async def test_should_return_exactly_the_callers_own_documents(self, project_feed_statements):
        project_feed_statements.given_two_accounts_each_with_documents()

        feed = await project_feed_statements.when_the_caller_requests_their_projects()

        project_feed_statements.assert_exactly_the_callers_own_items_are_returned(feed)
        project_feed_statements.assert_the_feed_was_queried_once_scoped_to_the_caller()
        project_feed_statements.assert_the_other_accounts_documents_are_absent(feed)

    async def test_should_refuse_an_unresolved_owner_without_querying_the_feed(
        self, project_feed_statements
    ):
        refusal = await project_feed_statements.when_an_unresolved_caller_requests_their_projects()

        project_feed_statements.assert_the_refusal_is_unauthenticated(refusal)
        project_feed_statements.assert_the_feed_was_never_queried()
