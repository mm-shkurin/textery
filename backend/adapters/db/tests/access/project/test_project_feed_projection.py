import pytest

from statements.project_feed_storage_statements import ProjectFeedStorageStatements


@pytest.mark.skip(
    reason="RED: AssertionError: every ProjectItem field must be projected from the "
    "document row -- kind, title, preview, document_type, status, retryable and both "
    "timestamps; and AssertionError: title and preview must be READ from documents.title "
    "and documents.content, not emitted as literals: a document seeded with a non-NULL "
    "title and non-empty content must surface both; and AssertionError: the row's "
    "timestamps must be the document's own, not a placeholder instant"
)
class TestProjectFeedRepositoryProjection:
    """Scenario 1.1: every row field is projected from the documents arm.

    Given an account holding one document written through the create-document
    usecase's storage port
    When that account's feed is read back through the feed read model
    Then the whole page equals a page carrying one row drawn from the stored
    document -- `kind` the literal `document`, `retryable` false, `title` and
    `preview` the stored title and content -- and both timestamps stay tz-aware.

    Owner scoping is `test_project_feed_storage.py`'s claim; this class only
    reads a single owner's single row and asks what that row holds.
    """

    async def test_should_project_every_contract_field_from_the_document(
        self, project_feed_statements: ProjectFeedStorageStatements
    ):
        owner_id = await project_feed_statements.given_an_account()
        document = await project_feed_statements.given_a_document_written_by_its_owner(owner_id)

        page = await project_feed_statements.list_feed(owner_id)

        project_feed_statements.assert_row_is_projected_from(page, document)

    async def test_should_project_title_and_preview_from_a_document_that_carries_them(
        self, project_feed_statements: ProjectFeedStorageStatements
    ):
        # The case the method above structurally cannot make. There the seeded
        # document is `Document.create`'s -- title NULL, content '' -- so the
        # expected `title=None`/`preview=''` are exactly what a projection that
        # never selects the two columns would emit, and the assertion passes
        # against a literal. Here the seeded values are neither NULL nor empty.
        owner_id = await project_feed_statements.given_an_account()
        document = await project_feed_statements.given_a_titled_document_written_by_its_owner(
            owner_id
        )

        page = await project_feed_statements.list_feed(owner_id)

        project_feed_statements.assert_titled_row_is_projected_from(page, document)

    async def test_should_keep_both_timestamps_tz_aware(
        self, project_feed_statements: ProjectFeedStorageStatements
    ):
        # Split from the field assertion on purpose: whole-page equality compares
        # instants, and two `datetime`s can be equal while one is naive only when
        # the other is too -- so an all-naive projection would satisfy equality
        # against a naive expectation and never say the word "tzinfo". This
        # method asks the question the contract actually cares about.
        owner_id = await project_feed_statements.given_an_account()
        await project_feed_statements.given_a_document_written_by_its_owner(owner_id)

        page = await project_feed_statements.list_feed(owner_id)

        project_feed_statements.assert_row_timestamps_are_tz_aware(page)
