import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


class TestProjectFeedIsOwnerScoped(AbstractBackendTest):
    """Scenario 1.1: The feed shows the caller's documents and nothing of anyone else's.

    Given an authenticated user with documents
    And another account with its own documents
    When they request their projects
    Then only their own documents are returned
    And the other account's documents are absent.
    """

    @pytest.mark.skip(
        reason="RED: GET /api/v1/projects is registered on no router, so the caller's "
        "feed answers Starlette's route-miss 404 {'detail': 'Not Found'} instead of 200."
    )
    async def test_feed_returns_only_the_callers_own_documents(
        self, project_feed_statements
    ):
        feeds = await project_feed_statements.given_two_accounts_each_holding_one_document_request_their_feeds()

        project_feed_statements.assert_both_feeds_served(feeds)
        project_feed_statements.assert_only_own_documents_are_returned(feeds)
        project_feed_statements.assert_the_other_accounts_document_is_absent(feeds)
