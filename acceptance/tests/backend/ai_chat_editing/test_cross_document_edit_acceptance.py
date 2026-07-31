import pytest

from statements.ai_edit.ai_edit_endpoints import EDIT_SCOPED_ENDPOINTS
from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: the scenario cannot be seeded — POST /documents/{id}/ai-edits is not "
    "mounted (main.py includes generation/auth/oauth/document only), so queueing the "
    "edit answers Starlette's fallback 404 {\"detail\":\"Not Found\"} instead of 202. "
    "All 3 items fail in setup: 'expected 202 queueing an edit on the caller's first "
    "document ..., got status_code=404'. Remove in green-acceptance."
)
class TestCrossDocumentEditAcceptance(AbstractBackendTest):
    @pytest.mark.parametrize("endpoint", EDIT_SCOPED_ENDPOINTS)
    async def test_should_not_find_an_edit_of_another_document_of_the_same_owner(
        self, ai_edit_cross_document_statements, endpoint
    ):
        """Scenario 1.2: An edit belonging to another document of the same owner is
        not found.

        Given an authenticated user owning two documents
        And an edit queued on the first document
        When the caller requests that edit under the second document's path
        Then the request is refused as not found
        And the edit is unchanged under its own document

        The second Then is not in the spec's scenario text: `/cancel` is one of the three
        probed endpoints, so a handler that terminalized the edit and only then answered
        404 would satisfy the refusal alone.

        Repeated for the stream, state and cancel endpoints — the path document id is
        authoritative.
        """
        setup = await ai_edit_cross_document_statements.given_an_edit_queued_on_the_first_of_two_owned_documents()
        probe = await ai_edit_cross_document_statements.when_the_edit_is_requested_under_the_second_documents_path(
            setup, endpoint
        )

        ai_edit_cross_document_statements.then_the_request_is_refused_as_not_found(probe)
        await ai_edit_cross_document_statements.then_the_edit_is_unchanged_under_its_own_document(
            probe
        )
