import uuid
from datetime import datetime, timezone
from typing import ClassVar

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.register_response_dto import RegisterResponseDto
from statements import auth_errors, duplicate_registration_scenarios as dup_scenarios
from statements.auth_scope import RegisterScope
from statements.response_assertions import (
    assert_duplicate_rejected,
    assert_no_account_created,
    assert_pending_account_created_with_verification_code,
    assert_server_owned_fields_ignored,
    assert_validation_error,
)

MALFORMED_EMAIL = "not-an-email"
OVERLONG_EMAIL_LOCAL_PART_LENGTH = 244


class AuthStatements:
    # Error dict literals live in auth_errors.py; kept accessible here as
    # ClassVar aliases since tests reference them as auth_statements.EXPECTED_*.
    EXPECTED_MALFORMED_EMAIL_ERROR: ClassVar[dict] = auth_errors.MALFORMED_EMAIL_ERROR
    EXPECTED_OVERLONG_EMAIL_ERROR: ClassVar[dict] = auth_errors.MALFORMED_EMAIL_ERROR
    EXPECTED_WEAK_PASSWORD_ERROR: ClassVar[dict] = auth_errors.WEAK_PASSWORD_ERROR
    EXPECTED_PASSWORD_MISMATCH_ERROR: ClassVar[dict] = auth_errors.PASSWORD_MISMATCH_ERROR
    EXPECTED_DUPLICATE_EMAIL_ERROR: ClassVar[dict] = auth_errors.DUPLICATE_EMAIL_ERROR
    ATTACKER_SUPPLIED_ID: ClassVar[str] = "11111111-1111-1111-1111-111111111111"

    def __init__(self, client: ApplicationClient):
        self._client = client
        self._last_request_window: tuple[datetime, datetime] | None = None

    async def given_registration_request_with_malformed_email(self) -> RegisterResponseDto:
        return await self._register_with_email(MALFORMED_EMAIL)

    async def given_registration_request_with_overlong_email(self) -> RegisterResponseDto:
        local_part = "a" * OVERLONG_EMAIL_LOCAL_PART_LENGTH
        overlong_email = f"{local_part}@example.com"
        assert len(overlong_email) == 256, (
            f"expected a 256-character email fixture, got {len(overlong_email)} chars"
        )
        return await self._register_with_email(overlong_email)

    async def given_registration_request_with_short_password(self) -> RegisterResponseDto:
        return await self._register_with_password("Ab1!abc")

    async def given_registration_request_with_password_missing_digit(self) -> RegisterResponseDto:
        return await self._register_with_password("Abcdefgh!")

    async def given_registration_request_with_password_missing_uppercase(self) -> RegisterResponseDto:
        return await self._register_with_password("abcdefg1!")

    async def given_registration_request_with_password_missing_lowercase(self) -> RegisterResponseDto:
        return await self._register_with_password("ABCDEFG1!")

    async def given_registration_request_with_password_missing_special_character(
        self,
    ) -> RegisterResponseDto:
        return await self._register_with_password("Abcdefg1")

    async def given_registration_request_with_overlong_password(self) -> RegisterResponseDto:
        password = "A1!" + "a" * 126
        assert len(password) == 129, (
            f"expected a 129-character password fixture, got {len(password)} chars"
        )
        return await self._register_with_password(password)

    async def given_registration_request_with_mismatched_confirm_password(
        self,
    ) -> RegisterResponseDto:
        scope = RegisterScope.builder(password="Str0ng!Pass", confirm_password="Different!9")
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def given_registration_request_with_server_owned_fields(
        self,
    ) -> RegisterResponseDto:
        scope = RegisterScope.builder(
            email="attacker@example.com",
            extra_fields={"is_verified": True, "id": self.ATTACKER_SUPPLIED_ID},
        )
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def given_valid_unique_registration_request(self) -> RegisterResponseDto:
        unique_email = f"user-{uuid.uuid4()}@example.com"
        scope = RegisterScope.builder(email=unique_email)
        request = scope.to_request_dto()
        # Bracket the call so the expiry assertion can check code_expires_at
        # against [sent_at + TTL, received_at + TTL] instead of a single
        # post-response "now" padded with a wide fixed tolerance - that would
        # hide a wrong TTL behind request latency.
        sent_at = datetime.now(timezone.utc)
        response = await self._client.register(request)
        received_at = datetime.now(timezone.utc)
        self._last_request_window = (sent_at, received_at)
        return response

    async def given_duplicate_registration_against_pending_account(
        self,
    ) -> RegisterResponseDto:
        return await dup_scenarios.given_duplicate_registration_against_pending_account(
            self._client
        )

    async def given_duplicate_registration_against_verified_account(
        self,
    ) -> RegisterResponseDto:
        return await dup_scenarios.given_duplicate_registration_against_verified_account(
            self._client
        )

    async def given_identical_registration_request_retried(
        self,
    ) -> RegisterResponseDto:
        return await dup_scenarios.given_identical_registration_request_retried(self._client)

    async def given_duplicate_registration_with_different_case(
        self,
    ) -> RegisterResponseDto:
        return await dup_scenarios.given_duplicate_registration_with_different_case(self._client)

    async def given_duplicate_registration_with_different_case_under_turkish_locale(
        self,
    ) -> RegisterResponseDto:
        return await (
            dup_scenarios.given_duplicate_registration_with_different_case_under_turkish_locale(
                self._client
            )
        )

    async def given_unicode_normalized_duplicate_registration(
        self,
    ) -> RegisterResponseDto:
        return await dup_scenarios.given_unicode_normalized_duplicate_registration(self._client)

    async def given_two_concurrent_registrations_for_same_new_email(
        self,
    ) -> tuple[RegisterResponseDto, RegisterResponseDto]:
        return await dup_scenarios.given_two_concurrent_registrations_for_same_new_email(
            self._client
        )

    def assert_exactly_one_account_created(
        self, responses: tuple[RegisterResponseDto, RegisterResponseDto]
    ) -> None:
        dup_scenarios.assert_exactly_one_account_created(
            responses, self.EXPECTED_DUPLICATE_EMAIL_ERROR
        )

    async def _register_with_email(self, email: str) -> RegisterResponseDto:
        scope = RegisterScope.builder(email=email)
        request = scope.to_request_dto()
        return await self._client.register(request)

    async def _register_with_password(self, password: str) -> RegisterResponseDto:
        scope = RegisterScope.builder(password=password, confirm_password=password)
        request = scope.to_request_dto()
        return await self._client.register(request)

    def assert_validation_error(self, response: RegisterResponseDto, expected_error: dict) -> None:
        assert_validation_error(response, expected_error)

    def assert_no_account_created(self, response: RegisterResponseDto) -> None:
        assert_no_account_created(response)

    def assert_rejected_as_duplicate(self, response: RegisterResponseDto) -> None:
        assert_duplicate_rejected(response, self.EXPECTED_DUPLICATE_EMAIL_ERROR)

    def assert_server_owned_fields_ignored(self, response: RegisterResponseDto) -> None:
        assert_server_owned_fields_ignored(response, self.ATTACKER_SUPPLIED_ID)

    def assert_pending_account_created_with_verification_code(
        self, response: RegisterResponseDto
    ) -> None:
        assert self._last_request_window is not None, (
            "assert_pending_account_created_with_verification_code requires the response "
            "from given_valid_unique_registration_request, which records the request window"
        )
        assert_pending_account_created_with_verification_code(response, self._last_request_window)
