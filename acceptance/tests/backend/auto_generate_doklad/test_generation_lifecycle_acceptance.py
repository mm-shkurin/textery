import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


class TestGenerationLifecycleAcceptance(AbstractBackendTest):
    """Scenarios 2.1 -> 4.1 -> 4.2: happy-path create -> pending -> completed content.

    Given a valid generation request for "доклад"
    When the client submits it and then polls the generation by id
    Then the create response is 201 pending
    And the generation eventually reaches "completed"
    And the completed generation returns the document content.
    """

    @pytest.mark.skip(reason="RED: green-acceptance re-enables — characterization of existing create→completed flow")
    async def test_should_create_pending_then_return_completed_document_content(self, generation_statements):
        create_response = await generation_statements.given_valid_generation_request_submitted()
        generation_statements.assert_generation_created_pending(create_response)

        completed_response = await generation_statements.await_generation_completed(create_response)

        generation_statements.assert_generation_completed_with_content(completed_response, create_response)
