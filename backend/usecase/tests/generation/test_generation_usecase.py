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
