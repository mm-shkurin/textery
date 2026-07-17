from shared.exceptions import ValidationException

EXPECTED_MISSING_TOPIC_MESSAGE = "topic is required"


class TestCreateGenerationRouter:
    """Scenario 1.1: Reject request with missing topic.

    Given a generation request without a topic
    When the client submits the request
    Then the response is a validation error
    And no generation is created
    """

    async def test_should_reject_missing_topic_with_400(self, mocker, create_client):
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(
            side_effect=ValidationException(EXPECTED_MISSING_TOPIC_MESSAGE)
        )

        async with create_client(mock_usecase, mocker.Mock()) as client:
            response = await client.post(
                "/api/v1/generations",
                json={"document_type": "доклад", "volume_pages": 3},
                headers={"Idempotency-Key": "test-key"},
            )

        assert response.status_code == 400, (
            f"expected 400 Bad Request for missing topic, got {response.status_code} "
            f"with body {response.text}"
        )
        assert response.json() == {
            "error_code": "VALIDATION_ERROR",
            "message": EXPECTED_MISSING_TOPIC_MESSAGE,
        }, (
            f"expected error body {{'error_code': 'VALIDATION_ERROR', "
            f"'message': '{EXPECTED_MISSING_TOPIC_MESSAGE}'}}, "
            f"got {response.json()}"
        )
