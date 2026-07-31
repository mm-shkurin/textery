import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: the scenario cannot be seeded — a revision is only recorded when an AI "
    "edit applies, and POST /documents/{id}/ai-edits is not mounted (main.py includes "
    "generation/auth/oauth/document only), so queueing the seed edit answers Starlette's "
    "fallback 404 {\"detail\":\"Not Found\"} instead of 202. 1 failed, 0 passed: "
    "'setup: expected 202 queueing an edit on the caller's first document ..., got "
    "status_code=404'. Remove in green-acceptance."
)
class TestCrossDocumentRevisionAcceptance(AbstractBackendTest):
    async def test_should_not_find_a_revision_of_another_document_of_the_same_owner(
        self, ai_edit_cross_revision_statements
    ):
        """Scenario 1.3: A revision belonging to another document of the same owner is
        not found.

        Given an authenticated user owning two documents
        And a revision recorded on the first document
        When the caller restores that revision number under the second document's path
        Then the request is refused as not found
        And no new version is created on either document

        One endpoint, not three: `POST /revisions/{n}/restore` is the only route that
        carries a revision number. The path document id is authoritative.
        """
        setup = await ai_edit_cross_revision_statements.given_a_revision_recorded_on_the_first_of_two_owned_documents()
        probe = await ai_edit_cross_revision_statements.when_the_revision_is_restored_under_the_second_documents_path(
            setup
        )

        ai_edit_cross_revision_statements.then_the_request_is_refused_as_not_found(probe)
        await ai_edit_cross_revision_statements.then_no_new_version_is_created_on_either_document(
            probe
        )
