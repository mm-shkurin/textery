import pytest

from tests.backend.abstract_backend_test import AbstractBackendTest


class TestCreateGenerationAcceptance(AbstractBackendTest):
    """Scenario 1.1: Reject request with missing topic.

    Given a generation request without a topic
    When the client submits the request
    Then the response is a validation error
    And no generation is created
    """

    async def test_should_reject_request_without_topic(self, generation_statements):
        response = await generation_statements.given_generation_request_submitted_without_topic()

        generation_statements.assert_validation_error(response, generation_statements.EXPECTED_MISSING_TOPIC_ERROR)
        generation_statements.assert_no_generation_created(response)

    @pytest.mark.parametrize("volume_pages", [0, 11], ids=["zero", "above_max"])
    async def test_should_reject_request_with_out_of_range_volume(self, generation_statements, volume_pages):
        """Scenario 1.2: Reject request with out-of-range volume.

        Given a generation request with an out-of-range volume_pages (0 or 11)
        When the client submits the request
        Then the response is a validation error
        And no generation is created
        """
        response = await generation_statements.given_generation_request_submitted_with_volume(volume_pages)

        generation_statements.assert_validation_error(
            response, generation_statements.EXPECTED_OUT_OF_RANGE_VOLUME_ERROR
        )
        generation_statements.assert_no_generation_created(response)

    @pytest.mark.skip(reason="RED: Scenario 2.1 - generation persistence and queueing not yet implemented")
    async def test_should_accept_and_queue_valid_request_without_waiting_on_llm(self, generation_statements):
        """Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call.

        Given a valid generation request for "доклад"
        When the client submits the request
        Then the response confirms the generation was created
        And the generation's status is "pending"
        And the response is returned without waiting for the document to be generated
        """
        response = await generation_statements.given_valid_generation_request_submitted()

        generation_statements.assert_generation_created_pending(response)
