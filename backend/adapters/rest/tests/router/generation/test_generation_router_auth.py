from uuid import uuid4

import pytest

from shared.exceptions import InvalidTokenException

_VALID_BODY = {"document_type": "доклад", "topic": "Как работает фотосинтез", "volume_pages": 3}


class TestCreateGenerationRequiresBearer:
    """Task 4: an anonymous caller cannot drive generation.

    The probe that filed this task got 201 for both of the first two cases. The
    assertion that no work reaches the usecase is the one that matters: a 401 that
    still enqueued the job would leave the GigaChat spend wide open.
    """

    async def test_should_return_401_without_an_authorization_header(
        self, mocker, unauthenticated_create_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()
        generate_document = mocker.Mock()
        generate_document.execute = mocker.AsyncMock()

        async with unauthenticated_create_client(usecase, generate_document) as client:
            response = await client.post("/api/v1/generations", json=_VALID_BODY)

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json()["error_code"] == "UNAUTHORIZED"
        usecase.execute.assert_not_awaited(), "no generation may be created without a token"
        generate_document.execute.assert_not_awaited(), "no LLM spend may happen without a token"

    @pytest.mark.parametrize(
        "header",
        ["Basic abc", "Bearer", "Bearer    ", "token-without-scheme", "Bearer garbage"],
        ids=["wrong-scheme", "no-token", "whitespace-token", "no-scheme", "garbage-token"],
    )
    async def test_should_return_401_for_an_unusable_header(
        self, mocker, unauthenticated_create_client, header
    ):
        # One answer for every shape of broken header. A distinct code per case would
        # tell an attacker which half they got right. "Bearer garbage" is the literal
        # header the reporting probe used.
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()
        generate_document = mocker.Mock()
        generate_document.execute = mocker.AsyncMock()

        async with unauthenticated_create_client(usecase, generate_document) as client:
            response = await client.post(
                "/api/v1/generations", json=_VALID_BODY, headers={"Authorization": header}
            )

        assert response.status_code == 401, f"{header!r} -> {response.status_code}: {response.text}"
        usecase.execute.assert_not_awaited()

    async def test_should_return_401_when_the_token_service_rejects_the_token(
        self, mocker, unauthenticated_create_client, generation_app
    ):
        # Covers expired, tampered, wrong-key, and -- the one that matters -- a
        # refresh token presented as a Bearer. read_access_subject enforces
        # type == "access", so a 7-day refresh token cannot buy a generation.
        from security.current_owner import get_token_service

        token_service = mocker.Mock()
        token_service.read_access_subject = mocker.Mock(side_effect=InvalidTokenException("nope"))
        generation_app.dependency_overrides[get_token_service] = lambda: token_service
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()
        generate_document = mocker.Mock()
        generate_document.execute = mocker.AsyncMock()

        async with unauthenticated_create_client(usecase, generate_document) as client:
            response = await client.post(
                "/api/v1/generations",
                json=_VALID_BODY,
                headers={"Authorization": "Bearer some.jwt.token"},
            )

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_not_awaited()


class TestGetGenerationRequiresBearer:
    """Task 4: reading a generation by id is not authorization."""

    async def test_should_return_401_without_an_authorization_header(
        self, mocker, unauthenticated_get_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_get_client(usecase) as client:
            response = await client.get(f"/api/v1/generations/{uuid4()}")

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json()["error_code"] == "UNAUTHORIZED"
        usecase.execute.assert_not_awaited()
