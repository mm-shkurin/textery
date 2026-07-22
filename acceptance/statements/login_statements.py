import uuid

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from clients.application.dto.auth.login_response_dto import LoginResponseDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from statements.response_assertions import assert_account_verified

# Provisional lockout threshold. The exact N is UNDECIDED (interview.md:50
# "exact N to be decided") — no threshold constant exists in code and no lockout
# ADR has been written yet, because red-acceptance runs BEFORE the 5.4 `design`
# step that ratifies N. 5 is a working value the test drives; the `design` step
# is responsible for confirming or amending it and locking the production value.
LOCKOUT_THRESHOLD = 5

CORRECT_PASSWORD = "Str0ng!Pass"
WRONG_PASSWORD = "Wr0ng!Pass"

# Distinct lockout taxonomy (spec 5.4 / DSL reference: "locked out" -> HTTP 403
# with a distinct error_code per case — must NOT reuse the not-verified 403 code).
ACCOUNT_LOCKED_ERROR_CODE = "ACCOUNT_LOCKED"


class LoginStatements:
    def __init__(self, client: ApplicationClient):
        self._client = client

    async def _register_and_verify_account(self) -> str:
        email = f"user-{uuid.uuid4()}@example.com"
        register_response = await self._client.register(
            RegisterRequestDto(
                email=email,
                password=CORRECT_PASSWORD,
                confirm_password=CORRECT_PASSWORD,
            )
        )
        code = register_response.body.get("verification_code")
        assert code is not None, (
            f"setup: expected registration to issue a verification_code, got body="
            f"{register_response.body}"
        )
        verify_response = await self._client.verify(VerifyRequestDto(email=email, code=code))
        assert_account_verified(verify_response)  # setup precondition: account is verified
        return email

    async def given_account_at_lockout_threshold_then_login_with_correct_password(
        self,
    ) -> LoginResponseDto:
        email = await self._register_and_verify_account()
        for _ in range(LOCKOUT_THRESHOLD):
            await self._client.login(LoginRequestDto(email=email, password=WRONG_PASSWORD))
        return await self._client.login(LoginRequestDto(email=email, password=CORRECT_PASSWORD))

    def assert_locked_out(self, response: LoginResponseDto) -> None:
        # Strict pin: 403 AND the distinct ACCOUNT_LOCKED error_code. Status alone
        # is insufficient — 403 is shared with not-verified (5.1), and the spec
        # requires a DISTINCT error_code per case, so reusing the not-verified code
        # would pass a status-only check for the wrong reason. Both must be checked.
        assert response.status_code == 403, (
            f"expected 403 Forbidden rejecting the locked-out account, got "
            f"status_code={response.status_code}, body={response.body}"
        )
        assert response.body is not None, (
            f"expected a lockout error body carrying error_code={ACCOUNT_LOCKED_ERROR_CODE!r}, "
            f"got body=None"
        )
        assert response.body.get("error_code") == ACCOUNT_LOCKED_ERROR_CODE, (
            f"expected the distinct lockout error_code {ACCOUNT_LOCKED_ERROR_CODE!r} "
            f"(must not reuse the not-verified 403 code), got body={response.body}"
        )
