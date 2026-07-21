import uuid
from dataclasses import dataclass

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.resend_request_dto import ResendRequestDto
from clients.application.dto.auth.resend_response_dto import ResendResponseDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from statements.response_assertions import (
    assert_account_verified,
    assert_already_verified_rejected,
)


@dataclass(frozen=True)
class ResendContext:
    email: str


COOLDOWN_ACTIVE_REJECTION = {
    "error_code": "RESEND_COOLDOWN_ACTIVE",
    "message": "A verification code was recently sent. Please wait before requesting another.",
}


class ResendStatements:
    def __init__(self, client: ApplicationClient):
        self._client = client

    async def _register_pending_account(self) -> ResendContext:
        email = f"user-{uuid.uuid4()}@example.com"
        register_request = RegisterRequestDto(
            email=email,
            password="Str0ng!Pass",
            confirm_password="Str0ng!Pass",
        )
        register_response = await self._client.register(register_request)
        assert register_response.body.get("verification_code") is not None, (
            f"setup: expected registration to issue a verification_code, got body="
            f"{register_response.body}"
        )
        return ResendContext(email=email)

    async def given_resend_for_pending_account(
        self,
    ) -> tuple[ResendResponseDto, ResendContext]:
        context = await self._register_pending_account()
        resend_response = await self._client.resend_code(ResendRequestDto(email=context.email))
        return resend_response, context

    async def given_resend_for_a_verified_account(self) -> ResendResponseDto:
        email = f"user-{uuid.uuid4()}@example.com"
        register_response = await self._client.register(
            RegisterRequestDto(
                email=email,
                password="Str0ng!Pass",
                confirm_password="Str0ng!Pass",
            )
        )
        code = register_response.body.get("verification_code")
        assert code is not None, (
            f"setup: expected registration to issue a verification_code, got body="
            f"{register_response.body}"
        )
        verify_response = await self._client.verify(VerifyRequestDto(email=email, code=code))
        assert_account_verified(verify_response)  # setup precondition: account is verified
        return await self._client.resend_code(ResendRequestDto(email=email))

    def assert_resend_rejected_as_cooldown_active(
        self, resend_response: ResendResponseDto
    ) -> None:
        # HTTP-observable pin for scenario 4.1: the resend endpoint is live and
        # the cooldown is enforced end-to-end. A just-registered account's code
        # is <60s old, so an immediate resend falls inside the cooldown window
        # and is rejected 429 RESEND_COOLDOWN_ACTIVE. The success path (a resend
        # >60s later issues a new code that supersedes the old) needs a
        # server-clock lever the acceptance layer lacks, so it is proven at the
        # usecase layer with a FakeClock (mirrors 3.6 / 2.4b / 3.4). Strict
        # status + body: a non-429 or a 400 carrying a different error_code would
        # pass a looser check for the wrong reason.
        assert resend_response.status_code == 429, (
            f"expected 429 Too Many Requests rejecting the in-cooldown resend, got "
            f"status_code={resend_response.status_code}, body={resend_response.body}"
        )
        assert resend_response.body == COOLDOWN_ACTIVE_REJECTION, (
            f"expected the cooldown-active rejection body {COOLDOWN_ACTIVE_REJECTION}, "
            f"got body={resend_response.body}"
        )

    def assert_resend_rejected_as_already_verified(
        self, resend_response: ResendResponseDto
    ) -> None:
        # Scenario 4.5: a resend against an already-verified account is rejected
        # 409 ALREADY_VERIFIED (reusing 3.5's taxonomy/message via the canonical
        # assert_already_verified_rejected helper, which pins status 409 AND the full
        # {error_code, message} body). Status is load-bearing, not just the error_code:
        # the is_verified gate must sit BEFORE the cooldown check, so a just-verified
        # account (whose registration code is <60s old) answers 409, NOT the 429
        # RESEND_COOLDOWN_ACTIVE it falls through to today. A body-only check would pass
        # on a wrong status carrying the right code.
        assert_already_verified_rejected(resend_response)
