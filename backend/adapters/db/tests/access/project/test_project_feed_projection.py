import pytest


@pytest.mark.skip(
    reason="RED: AssertionError: every ProjectItem field must be projected from the "
    "document row -- kind, title, preview, document_type, status, retryable and both "
    "timestamps; and AssertionError: the row's timestamps must be the document's own, "
    "not a placeholder instant"
)
class TestProjectFeedRepositoryProjection:
    """Scenario 1.1: every row field is projected from the documents arm.

    Given an account holding one document written through the create-document
    usecase's storage port
    When that account's feed is read back through the feed read model
    Then the row carries all nine contract fields drawn from the stored document
    -- `kind` the literal `document`, `retryable` false, `preview` `''` for empty
    content, `title` the stored NULL -- and both timestamps stay tz-aware.

    Owner scoping is `test_project_feed_storage.py`'s claim; this class only
    reads a single owner's single row and asks what that row holds.
    """

    async def test_should_project_every_contract_field_from_the_document(
        self, project_feed_statements
    ):
        owner_id = await project_feed_statements.given_an_account()
        document = await project_feed_statements.given_a_document_written_by_its_owner(owner_id)

        page = await project_feed_statements.list_feed(owner_id)

        project_feed_statements.assert_row_is_projected_from(page, document)

    async def test_should_keep_both_timestamps_tz_aware(self, project_feed_statements):
        # Split from the field assertion on purpose: whole-row equality compares
        # instants, and two `datetime`s can be equal while one is naive only when
        # the other is too -- so an all-naive projection would satisfy equality
        # against a naive expectation and never say the word "tzinfo". This
        # method asks the question the contract actually cares about.
        owner_id = await project_feed_statements.given_an_account()
        await project_feed_statements.given_a_document_written_by_its_owner(owner_id)

        page = await project_feed_statements.list_feed(owner_id)

        project_feed_statements.assert_row_timestamps_are_tz_aware(page)
