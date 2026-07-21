from datetime import UTC, datetime

import pytest

from statements.verification_code_storage_statements import VerificationCodeStorageStatements

_KNOWN_PAST_CREATED_AT = datetime(2020, 1, 1, tzinfo=UTC)


class TestSave:
    """Saving a verification code persists id, account_id, code (byte-exact
    string), expires_at, and consumed_at=None exactly as passed in."""

    async def test_should_round_trip_saved_verification_code(
        self, verification_code_storage_statements: VerificationCodeStorageStatements
    ):
        account = await verification_code_storage_statements.given_saved_account()
        code = verification_code_storage_statements.build_code_for_account(account)
        await verification_code_storage_statements.save_code(code)
        await verification_code_storage_statements.fetch_saved_code_row()
        verification_code_storage_statements.assert_fetched_matches_saved()


class TestSaveGeneratedCode:
    """A code produced by VerificationCode.generate() -- the /register path --
    reaches the String(6) column as a plain str and round-trips unchanged."""

    async def test_should_round_trip_generated_verification_code(
        self, verification_code_storage_statements: VerificationCodeStorageStatements
    ):
        account = await verification_code_storage_statements.given_saved_account()
        code = verification_code_storage_statements.build_generated_code_for_account(account)
        await verification_code_storage_statements.save_code(code)
        await verification_code_storage_statements.fetch_saved_code_row()
        verification_code_storage_statements.assert_fetched_code_is_the_generated_str()


@pytest.mark.skip(
    reason="RED: save() stamps datetime.now(UTC) at insert, discarding code.created_at "
    "(verification_code_storage.py:69 / from_domain created_at param). Story 7 4.1 green-adapter."
)
class TestSavePersistsDomainCreatedAt:
    """save() must persist the domain object's own created_at (the instant issued
    from the injected Clock), not a wall-clock stamp. The resend-cooldown gate
    (scenario 4.1) reads code.created_at; if save() overwrites it with
    datetime.now(UTC) the persisted/read-back value disagrees with the domain
    value under any Clock/wall-clock skew. Issue a code with a known past
    created_at, round-trip through the repository, and assert it survives."""

    async def test_should_persist_domain_created_at_not_wall_clock(
        self, verification_code_storage_statements: VerificationCodeStorageStatements
    ):
        account = await verification_code_storage_statements.given_saved_account()
        code = verification_code_storage_statements.build_code_with_created_at(
            account, _KNOWN_PAST_CREATED_AT
        )
        await verification_code_storage_statements.save_code(code)
        await verification_code_storage_statements.reload_active_code(account.id)
        verification_code_storage_statements.assert_reloaded_code_matches_saved(
            _KNOWN_PAST_CREATED_AT
        )
