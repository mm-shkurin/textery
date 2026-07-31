import pytest

from statements.ai_edit.ai_edit_endpoints import ALL_ENDPOINTS
from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: none of the seven AI-edit routes exist yet, so a refusal cannot be "
    "told apart from an unrouted request and the owner's own history is not "
    "readable. Remove in green-acceptance."
)
class TestDocumentScopeGuardAcceptance(AbstractBackendTest):
    @pytest.mark.parametrize("endpoint", ALL_ENDPOINTS)
    async def test_should_refuse_absent_document_indistinguishably_from_foreign_one(
        self, ai_edit_guard_statements, endpoint
    ):
        """Scenario 1.1: Every endpoint refuses an absent document indistinguishably
        from a foreign one.

        Given an authenticated user
        And a document owned by another account
        When the caller invokes <endpoint> against it
        And the caller invokes <endpoint> against a document id that does not exist
        Then both are refused as not found
        And the two response bodies are byte-identical
        And no edit, revision or message is created
        """
        setup = await ai_edit_guard_statements.given_a_foreign_document_and_an_absent_document_id()
        probe = await ai_edit_guard_statements.when_the_endpoint_is_invoked_against_both(
            setup, endpoint
        )
        aftermath = await ai_edit_guard_statements.when_the_owner_reads_the_document_aftermath(
            probe
        )

        ai_edit_guard_statements.then_both_are_refused_as_not_found(probe)
        ai_edit_guard_statements.then_the_two_response_bodies_are_byte_identical(probe)
        ai_edit_guard_statements.then_no_edit_revision_or_message_is_created(probe, aftermath)
