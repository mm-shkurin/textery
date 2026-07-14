import pytest

from statements.verification_code_storage_statements import VerificationCodeStorageStatements


@pytest.mark.skip(reason="RED: SqlAlchemyVerificationCodeRepository.save not implemented")
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
