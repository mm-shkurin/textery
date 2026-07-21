import uuid
from dataclasses import dataclass

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.resend_request_dto import ResendRequestDto
from clients.application.dto.auth.resend_response_dto import ResendResponseDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from clients.application.dto.auth.verify_response_dto import VerifyResponseDto
from statements.response_assertions import assert_account_verified
from statements.verification_code_assertions import assert_valid_verification_code


@dataclass(frozen=True)
class ResendContext:
    email: str
    old_code: str


SUPERSEDED_CODE_REJECTION = {
    "error_code": "INVALID_OR_EXPIRED_CODE",
    "message": "The verification code is invalid or has expired.",
}

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
        old_code = register_response.body.get("verification_code")
        assert old_code is not None, (
            f"setup: expected registration to return a verification_code, got body="
            f"{register_response.body}"
        )
        return ResendContext(email=email, old_code=old_code)

    async def given_resend_for_pending_account(
        self,
    ) -> tuple[ResendResponseDto, ResendContext]:
        context = await self._register_pending_account()
        resend_response = await self._client.resend_code(ResendRequestDto(email=context.email))
        return resend_response, context

    async def when_old_and_new_codes_submitted(
        self, resend_response: ResendResponseDto, context: ResendContext
    ) -> tuple[VerifyResponseDto, VerifyResponseDto]:
        new_code = resend_response.body.get("verification_code")
        old_verify = await self._client.verify(
            VerifyRequestDto(email=context.email, code=context.old_code)
        )
        new_verify = await self._client.verify(
            VerifyRequestDto(email=context.email, code=new_code)
        )
        return old_verify, new_verify

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

    def assert_new_code_issued(
        self, resend_response: ResendResponseDto, context: ResendContext
    ) -> None:
        assert resend_response.status_code == 200, (
            f"expected 200 OK from resend, got status_code={resend_response.status_code}, "
            f"body={resend_response.body}"
        )
        new_code = resend_response.body.get("verification_code") if resend_response.body else None
        assert_valid_verification_code(new_code)
        assert new_code != context.old_code, (
            f"expected resend to issue a new code different from the previous "
            f"{context.old_code!r}, got the same code {new_code!r}"
        )

    def assert_old_code_no_longer_verifies(self, old_verify: VerifyResponseDto) -> None:
        # Strict, not "non-200": the superseded old code is submitted while the
        # account is still pending, so /verify answers the generic client-safe
        # rejection (auth_verify.yaml 400; error_code INVALID_OR_EXPIRED_CODE,
        # which is absent from the status map and therefore maps to 400). A
        # non-200 check would pass for the wrong reason on a 500, on a 409
        # ALREADY_VERIFIED, or on a 400 carrying any other error_code.
        assert old_verify.status_code == 400, (
            f"expected 400 Bad Request rejecting the superseded code, got "
            f"status_code={old_verify.status_code}, body={old_verify.body}"
        )
        assert old_verify.body == SUPERSEDED_CODE_REJECTION, (
            f"expected the superseded-code rejection body {SUPERSEDED_CODE_REJECTION}, "
            f"got body={old_verify.body}"
        )

    def assert_new_code_verifies(self, new_verify: VerifyResponseDto) -> None:
        # The verified end-state (200 + {"is_verified": True}) is the shared
        # /verify success contract owned by assert_account_verified — reuse it
        # rather than re-encoding it, exactly as VerifyStatements does.
        assert_account_verified(new_verify)
