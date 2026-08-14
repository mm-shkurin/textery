"""Statements for `POST /api/v1/auth/me/deletion` over real HTTP.

Every account here is made through the public API — register/verify/login for a
password account, and the OAuth callback/exchange legs (against the backend's
fake provider) for an account that has NO password. The second one cannot be
faked at this level and must not be: the claim is about an account whose stored
`password_hash` really is `""`, which only the OAuth path produces.
"""

import uuid
from dataclasses import dataclass

from clients.application.application_client import ApplicationClient
from clients.application.dto.auth.deletion_response_dto import DeletionResponseDto
from clients.application.dto.auth.profile_response_dto import ProfileResponseDto
from clients.application.dto.auth.register_request_dto import RegisterRequestDto
from clients.application.dto.auth.verify_request_dto import VerifyRequestDto
from clients.application.dto.auth.login_request_dto import LoginRequestDto
from statements.account_setup import ACCOUNT_PASSWORD
from statements.oauth_statements import OAuthStatements

CONFIRMATION_INVALID = "DELETION_CONFIRMATION_INVALID"
UNAUTHORIZED = 401
NO_CONTENT = 204


@dataclass(frozen=True)
class OAuthAttempts:
    empty_password: DeletionResponseDto
    someone_elses_email: DeletionResponseDto
    own_email: DeletionResponseDto


@dataclass(frozen=True)
class DeletedSession:
    deletion: DeletionResponseDto
    profile_after: ProfileResponseDto


class DeletionStatements:
    def __init__(self, client: ApplicationClient) -> None:
        self._client = client
        self._oauth = OAuthStatements(client)

    async def delete_a_password_account_then_reuse_its_token(self) -> DeletedSession:
        token, _ = await self._password_account()
        deletion = await self._client.delete_account({"password": ACCOUNT_PASSWORD}, token)
        # The SAME token, which is still cryptographically valid for up to fifteen
        # minutes. Nothing revokes it; get_current_owner_id checks the account row
        # exists on every authenticated request, which is what makes the deletion
        # effective in every tab and on every device immediately.
        return DeletedSession(deletion=deletion, profile_after=await self._client.get_me(token))

    async def confirm_a_password_account_with_its_own_email(self) -> DeletionResponseDto:
        token, email = await self._password_account()
        # The correct address, on an account that HAS a password. It must not
        # delete: the deletion screen shows the user their own email, so accepting
        # it here would reduce the password gate to reading the page.
        return await self._client.delete_account({"confirm_email": email}, token)

    async def try_every_confirmation_on_an_oauth_account(self) -> OAuthAttempts:
        email = f"oauth-deletion-{uuid.uuid4()}@example.com"
        exchanged = await self._oauth.exchange(await self._oauth.handoff_code(email=email))
        token = self._access_token_of(exchanged)
        return OAuthAttempts(
            # The stored hash IS the empty string. A check written as "does the
            # submitted value match the stored one" deletes the account on this.
            empty_password=await self._client.delete_account({"password": ""}, token),
            someone_elses_email=await self._client.delete_account(
                {"confirm_email": f"neighbour-{uuid.uuid4()}@example.com"}, token
            ),
            own_email=await self._client.delete_account({"confirm_email": email}, token),
        )

    def assert_the_session_is_dead_immediately(self, outcome: DeletedSession) -> None:
        assert outcome.deletion.status_code == NO_CONTENT, (
            f"expected the deletion to answer {NO_CONTENT}, got "
            f"status_code={outcome.deletion.status_code}, body={outcome.deletion.body!r}"
        )
        assert outcome.profile_after.status_code == UNAUTHORIZED, (
            f"expected the still-unexpired access token to be refused with "
            f"{UNAUTHORIZED} once its account is gone, got "
            f"status_code={outcome.profile_after.status_code}, "
            f"body={outcome.profile_after.body!r}"
        )

    def assert_refused(self, response: DeletionResponseDto, described_as: str) -> None:
        assert response.status_code == 400, (
            f"expected {described_as} to be refused with 400 — the session is valid, it is "
            f"the confirmation that failed — got status_code={response.status_code}, "
            f"body={response.body!r}"
        )
        assert response.body is not None and response.body.get("error_code") == (
            CONFIRMATION_INVALID
        ), (
            f"expected {described_as} to answer error_code={CONFIRMATION_INVALID} in the "
            f"canonical envelope, got {response.body!r}"
        )

    def assert_only_the_own_email_deleted(self, attempts: OAuthAttempts) -> None:
        self.assert_refused(attempts.empty_password, "an empty password on an OAuth account")
        self.assert_refused(attempts.someone_elses_email, "someone else's address")
        assert attempts.own_email.status_code == NO_CONTENT, (
            f"expected the account's own address to confirm the deletion with "
            f"{NO_CONTENT}, got status_code={attempts.own_email.status_code}, "
            f"body={attempts.own_email.body!r}"
        )

    async def _password_account(self) -> tuple[str, str]:
        email = f"deletion-{uuid.uuid4()}@example.com"
        registration = await self._client.register(
            RegisterRequestDto(
                email=email, password=ACCOUNT_PASSWORD, confirm_password=ACCOUNT_PASSWORD
            )
        )
        code = self._required(registration, "verification_code")
        await self._client.verify(VerifyRequestDto(email=email, code=code))
        login = await self._client.login(
            LoginRequestDto(email=email, password=ACCOUNT_PASSWORD)
        )
        return self._required(login, "access_token"), email

    @staticmethod
    def _access_token_of(exchanged) -> str:
        assert exchanged.body is not None and exchanged.body.get("access_token"), (
            f"setup: expected the OAuth exchange to issue an access_token, got "
            f"status_code={exchanged.status_code}, body={exchanged.body!r}"
        )
        return exchanged.body["access_token"]

    @staticmethod
    def _required(response, key: str):
        assert response.body is not None, (
            f"setup: expected a body carrying {key}, got status_code={response.status_code}"
        )
        value = response.body.get(key)
        assert value is not None, (
            f"setup: expected {key}, got status_code={response.status_code}, "
            f"body={response.body}"
        )
        return value
