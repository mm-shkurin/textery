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

        generation_statements.assert_missing_topic_error(response)
        generation_statements.assert_no_generation_created(response)

    @pytest.mark.skip(
        reason="RED: Generation.create() does not validate volume_pages yet -- "
        "falls through to NotImplementedError, caught by the catch-all handler as 500"
    )
    async def test_should_reject_request_with_zero_volume(self, generation_statements):
        """Scenario 1.2: Reject request with out-of-range volume.

        Given a generation request with volume_pages of 0
        When the client submits the request
        Then the response is a validation error
        And no generation is created
        """
        response = await generation_statements.given_generation_request_submitted_with_volume(0)

        generation_statements.assert_out_of_range_volume_error(response)
        generation_statements.assert_no_generation_created(response)

    @pytest.mark.skip(
        reason="RED: Generation.create() does not validate volume_pages yet -- "
        "falls through to NotImplementedError, caught by the catch-all handler as 500"
    )
    async def test_should_reject_request_with_volume_above_max(self, generation_statements):
        """Scenario 1.2: Reject request with out-of-range volume.

        Given a generation request with volume_pages of 11
        When the client submits the request
        Then the response is a validation error
        And no generation is created
        """
        response = await generation_statements.given_generation_request_submitted_with_volume(11)

        generation_statements.assert_out_of_range_volume_error(response)
        generation_statements.assert_no_generation_created(response)
