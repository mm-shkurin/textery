import pytest

from statements.generation_statements import GenerationStatements

INVISIBLE_CHAR_TOPIC = "​"


class TestGenerationUsecase:
    """Scenario 1.1: Reject request with missing topic.

    Given a generation request without a topic
    When the client submits the request
    Then the response is a validation error
    And no generation is created
    """

    @pytest.mark.parametrize(
        "topic",
        [None, "", "   ", INVISIBLE_CHAR_TOPIC],
        ids=["omitted_null", "empty_string", "whitespace_only", "invisible_char_only"],
    )
    def test_should_reject_missing_topic(self, generation_statements: GenerationStatements, topic):
        generation_statements.attempt_creating_generation_with_topic(topic)
        generation_statements.assert_missing_topic_error_raised()


class TestGenerationUsecaseVolumeRange:
    """Scenario 1.2: Reject request with out-of-range volume.

    Given a generation request with volume_pages of 0
    When the client submits the request
    Then the response is a validation error
    And no generation is created

    Given a generation request with volume_pages of 11
    When the client submits the request
    Then the response is a validation error
    And no generation is created
    """

    @pytest.mark.parametrize(
        "volume_pages",
        [0, 11, None, -1, 999999999999],
        ids=["zero", "eleven", "omitted_null", "negative", "extreme_out_of_range"],
    )
    def test_should_reject_out_of_range_volume(self, generation_statements: GenerationStatements, volume_pages):
        generation_statements.attempt_creating_generation_with_volume_pages(volume_pages)
        generation_statements.assert_out_of_range_volume_error_raised()


class TestGenerationUsecaseHappyPath:
    """Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call.

    Given a valid generation request for "доклад"
    When the client submits the request
    Then the response confirms the generation was created
    And the generation's status is "pending"
    And the response is returned without waiting for the document to be generated
    """

    async def test_should_return_pending_generation_and_enqueue_job(
        self, generation_statements: GenerationStatements
    ):
        await generation_statements.submit_valid_generation_request()
        generation_statements.assert_generation_accepted_and_pending()
        generation_statements.assert_generation_persisted_exactly_once()
        generation_statements.assert_generation_enqueued_exactly_once()
        generation_statements.assert_save_happened_before_enqueue()
