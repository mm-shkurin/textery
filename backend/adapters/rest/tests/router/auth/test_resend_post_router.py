from datetime import UTC, datetime
from uuid import uuid4

from auth.verification_code import VerificationCode


class TestResendPostRouterNewCode:
    """Scenario 4.1: Resend issues a new verification code.

    Given the resend usecase issues a fresh, unexpired VerificationCode for a
    pending account (email is mocked; no real email is sent)
    When the client submits POST /api/v1/auth/resend-code with {email}
    Then the response is 200 with a ResendResponseDto-shaped body carrying the
    new verification_code and its code_expires_at, built from the domain
    VerificationCode
    And the usecase is awaited once with the submitted email
    """

    async def test_should_return_200_with_new_verification_code_and_expiry(
        self, mocker, resend_client
    ):
        code_expires_at = datetime(2026, 7, 21, 12, 40, 0, tzinfo=UTC)
        issued_code = VerificationCode.create(
            id=uuid4(),
            account_id=uuid4(),
            code="778201",
            expires_at=code_expires_at,
            created_at=datetime.now(UTC),
        )
        mock_usecase = mocker.Mock()
        mock_usecase.execute = mocker.AsyncMock(return_value=issued_code)

        async with resend_client(mock_usecase) as client:
            response = await client.post(
                "/api/v1/auth/resend-code",
                json={"email": "pending-user@example.com"},
            )

        assert response.status_code == 200, (
            f"expected 200 OK, got {response.status_code} with body {response.text}"
        )
        body = response.json()
        assert body == {
            "verification_code": "778201",
            "code_expires_at": code_expires_at.isoformat(),
        }, (
            f"expected the exact ResendResponseDto body carrying verification_code='778201' "
            f"and code_expires_at={code_expires_at.isoformat()!r} from the issued "
            f"VerificationCode -- no more, no fewer fields; got body={body}"
        )
        mock_usecase.execute.assert_awaited_once_with(email="pending-user@example.com")
