from datetime import UTC, datetime

from statements.verification_code_storage_statements import VerificationCodeStorageStatements

_KNOWN_PAST_CREATED_AT = datetime(2020, 1, 1, tzinfo=UTC)
_KNOWN_CONSUMED_AT = datetime(2020, 1, 1, 0, 5, tzinfo=UTC)


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


class TestSavePreservesCreatedAtOnUpdate:
    """save()'s UPDATE branch (consume) must never rewrite created_at.

    find_active_by_account_id orders by created_at desc, so supersession and the
    resend cooldown (scenario 4.1) depend on created_at staying the code's real
    issuance instant. save() has two paths -- insert (new row) and update (stamp
    consumed_at on an existing row). The insert test above guards the insert path;
    this guards that consuming a code and re-saving it (the update path) leaves
    created_at at the value it was issued with, while proving the update really
    happened (consumed_at now set). Issue a code with a known past created_at,
    reload it, consume-and-resave through the update branch, reload again, and
    assert created_at is still T0 and consumed_at is set."""

    async def test_should_preserve_created_at_through_consume_update(
        self, verification_code_storage_statements: VerificationCodeStorageStatements
    ):
        account = await verification_code_storage_statements.given_saved_account()
        code = verification_code_storage_statements.build_code_with_created_at(
            account, _KNOWN_PAST_CREATED_AT
        )
        await verification_code_storage_statements.save_code(code)
        await verification_code_storage_statements.reload_active_code(account.id)
        await verification_code_storage_statements.consume_and_resave_reloaded_code(
            _KNOWN_CONSUMED_AT
        )
        await verification_code_storage_statements.reload_active_code(account.id)
        verification_code_storage_statements.assert_created_at_survived_update(
            _KNOWN_PAST_CREATED_AT, _KNOWN_CONSUMED_AT
        )
