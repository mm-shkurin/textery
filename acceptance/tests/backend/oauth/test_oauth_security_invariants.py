from statements.oauth_runtime_probe import backend_logs, boot_with_blank_provider_config
from statements.oauth_scope import (
    FRONTEND_CALLBACK_PATH,
    INVALID_CODE_ERROR,
    path_of,
    query_param,
    unique_email,
    unique_subject,
)
from statements.oauth_statements import SESSION_FIELDS, account_id_of
from tests.backend.abstract_backend_test import AbstractBackendTest

JWT_PREFIX = "eyJ"


class TestOAuthSecurityInvariants(AbstractBackendTest):
    """The OAuth security gate (I1-I8). Green at the end of every work unit.

    These tests are not a working surface: when one goes red the production code is
    fixed or the work stops. Weakening, skipping or xfailing an assertion here is
    never the fix — each one stands for a way real users get hurt, not for a
    convention.
    """

    async def test_i1_forged_state_is_refused_and_yields_no_session(self, oauth_statements):
        redirect = await oauth_statements.callback(
            code="sub=attacker;email=attacker@example.com", state="forged-state"
        )

        assert query_param(redirect.location, "code") is None, (
            f"a forged state minted a handoff code: {redirect.location}"
        )
        assert query_param(redirect.location, "error"), (
            f"a forged state must come back as an error, got {redirect.location}"
        )

    async def test_i1_missing_state_is_refused(self, oauth_statements):
        redirect = await oauth_statements.callback(code="sub=nobody;email=nobody@example.com")

        assert query_param(redirect.location, "code") is None, (
            f"a callback with no state minted a handoff code: {redirect.location}"
        )
        assert query_param(redirect.location, "error")

    async def test_i1_state_is_single_use(self, oauth_statements):
        state = await oauth_statements.minted_state()
        code = "sub=replayer;email=replayer@example.com"

        first = await oauth_statements.callback(code=code, state=state)
        replayed = await oauth_statements.callback(code=code, state=state)

        assert query_param(first.location, "code"), f"first leg should succeed: {first.location}"
        assert query_param(replayed.location, "code") is None, (
            f"a replayed state minted a second handoff code: {replayed.location}"
        )

    async def test_i2_concurrent_exchanges_yield_exactly_one_session(self, oauth_statements):
        code = await oauth_statements.handoff_code()

        first, second = await oauth_statements.exchange_twice_concurrently(code)

        statuses = sorted([first.status_code, second.status_code])
        assert statuses == [200, 400], (
            f"exactly one concurrent exchange may succeed, got {statuses}"
        )

    async def test_i3_expired_handoff_code_does_not_exchange(self, oauth_statements, expired_code):
        response = await oauth_statements.exchange(expired_code)

        assert response.status_code == 400
        assert response.body["error_code"] == INVALID_CODE_ERROR

    async def test_i4_no_token_rides_in_a_redirect(self, oauth_statements):
        start = await oauth_statements.start()
        callback = await oauth_statements.completed_callback()

        for location in (start.location, callback.location):
            assert JWT_PREFIX not in location, f"a JWT rode in a redirect URL: {location}"
        assert path_of(callback.location) == FRONTEND_CALLBACK_PATH
        assert query_param(callback.location, "code"), "only an opaque handoff code may ride here"

    async def test_i4_tokens_are_returned_only_in_the_exchange_body(self, oauth_statements):
        response = await oauth_statements.signed_in_session()

        assert response.status_code == 200
        for field in SESSION_FIELDS:
            assert response.body[field], f"{field} missing from the exchange body"

    async def test_i5_no_handoff_code_or_token_reaches_the_logs(self, oauth_statements):
        code = await oauth_statements.handoff_code()
        session = await oauth_statements.exchange(code)
        logs = backend_logs()

        assert code not in logs, "the handoff code was written to the logs"
        assert session.body["access_token"] not in logs, "an access token was written to the logs"
        assert session.body["refresh_token"] not in logs, "a refresh token reached the logs"

    async def test_i5_no_provider_secret_reaches_the_logs(self, oauth_statements, provider_secret):
        await oauth_statements.signed_in_session()

        assert provider_secret not in backend_logs(), "the provider secret reached the logs"

    async def test_i6_one_identity_per_provider_subject(self, oauth_statements):
        subject, email = unique_subject(), unique_email()

        first = await oauth_statements.exchange(
            await oauth_statements.handoff_code(subject=subject, email=email)
        )
        second = await oauth_statements.exchange(
            await oauth_statements.handoff_code(subject=subject, email=email.upper())
        )

        assert first.status_code == 200 and second.status_code == 200
        # The account id is read out of the token subject rather than counted in the
        # database: acceptance is black-box, and "both sign-ins resolved to the same
        # account" is exactly what a second row would break.
        assert account_id_of(first) == account_id_of(second), (
            "a case-variant email for one provider subject resolved to a second account"
        )

    async def test_i7_blank_provider_config_fails_the_boot(self):
        result = boot_with_blank_provider_config()

        assert result.returncode != 0, (
            "the app booted with a blank provider client id instead of failing fast"
        )
        assert "YANDEX_CLIENT_ID" in (result.stdout + result.stderr), (
            "the boot failure must name the missing variable"
        )

    async def test_i8_oauth_email_does_not_link_into_a_password_account(self, oauth_statements):
        email, password = await oauth_statements.given_password_account()

        redirect = await oauth_statements.completed_callback(email=email)

        assert query_param(redirect.location, "code") is None, (
            "an OAuth sign-in silently adopted an existing password account: "
            f"{redirect.location}"
        )
        assert query_param(redirect.location, "error")
        assert await oauth_statements.can_still_log_in_with_password(email, password), (
            "the password account was mutated by an OAuth sign-in"
        )
