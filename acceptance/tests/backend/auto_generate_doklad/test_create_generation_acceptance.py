import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


@pytest.mark.skip(
    reason="RED: backend/ has no FastAPI app yet (placeholder http.server) -- "
    "POST /api/v1/generations returns 501 Unsupported method instead of 400"
)
class TestCreateGenerationAcceptance(AbstractBackendTest):
    """Scenario 1.1: Reject request with missing topic.

    Given a generation request without a topic
    When the client submits the request
    Then the response is a validation error
    And no generation is created
    """

    async def test_should_reject_request_without_topic(self, generation_statements):
        response = await generation_statements.given_generation_request_submitted_without_topic()

        generation_statements.assert_missing_topic_error(response)
        generation_statements.assert_no_generation_created(response)
