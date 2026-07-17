from uuid import uuid4

import pytest

from shared.exceptions import InvalidTokenException


class TestVersionFieldIsStrict:
    """Scenario 8.1: a non-integer version is rejected, not coerced into a valid token.

    This exists because Pydantic v2's LAX mode (the default) coerces "5" and 5.0 to
    5. So a plain `version: int` would ACCEPT two of the three values 8.1 calls
    non-integer, and they would act as a real CAS token. StrictInt is the fix, and
    without a test nothing would ever reveal the difference -- both spellings look
    identical in review.
    """

    @pytest.mark.parametrize(
        "version",
        ["5", 1.5, True, "abc", None],
        ids=["numeric-string", "float", "bool", "text", "null"],
    )
    async def test_should_reject_a_non_integer_version(self, mocker, save_client, version):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with save_client(usecase) as client:
            response = await client.put(
                f"/api/v1/documents/{uuid4()}",
                json={"content": "<p>x</p>", "version": version},
            )

        assert response.status_code == 422, (
            f"version={version!r} must be rejected, got {response.status_code}: {response.text}"
        )
        usecase.execute.assert_not_awaited(), "a bad version must never reach the usecase"


class TestBearerIsRequired:
    """Security 7.2: every document endpoint rejects an absent or unusable token."""

    async def test_should_return_401_without_an_authorization_header(
        self, mocker, unauthenticated_create_client
    ):
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_create_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents",
                json={"document_type": "эссе"},
                headers={"Idempotency-Key": "key-1"},
            )

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json()["error_code"] == "UNAUTHORIZED"
        usecase.execute.assert_not_awaited(), "no document work may happen without a token"

    @pytest.mark.parametrize(
        "header",
        ["Basic abc", "Bearer", "Bearer    ", "token-without-scheme"],
        ids=["wrong-scheme", "no-token", "whitespace-token", "no-scheme"],
    )
    async def test_should_return_401_for_an_unusable_header(
        self, mocker, unauthenticated_create_client, document_app, header
    ):
        # One answer for every shape of broken header. A distinct code per case would
        # tell an attacker which half they got right.
        from security.current_owner import get_token_service

        document_app.dependency_overrides[get_token_service] = lambda: mocker.Mock()
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_create_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents",
                json={"document_type": "эссе"},
                headers={"Idempotency-Key": "key-1", "Authorization": header},
            )

        assert response.status_code == 401, f"{header!r} -> {response.status_code}: {response.text}"

    async def test_should_return_401_when_the_token_service_rejects_the_token(
        self, mocker, unauthenticated_create_client, document_app
    ):
        # Covers expired, tampered, wrong-key, and -- the one that matters -- a
        # refresh token presented as a Bearer. JwtTokenService.read_access_subject
        # raises InvalidTokenException for all of them.
        from security.current_owner import get_token_service

        token_service = mocker.Mock()
        token_service.read_access_subject = mocker.Mock(side_effect=InvalidTokenException("nope"))
        document_app.dependency_overrides[get_token_service] = lambda: token_service
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_create_client(usecase) as client:
            response = await client.post(
                "/api/v1/documents",
                json={"document_type": "эссе"},
                headers={"Idempotency-Key": "key-1", "Authorization": "Bearer some.jwt.token"},
            )

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        usecase.execute.assert_not_awaited()
