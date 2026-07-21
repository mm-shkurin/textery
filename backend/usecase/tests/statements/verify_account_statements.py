from datetime import timedelta
from uuid import uuid4

from auth.account import Account
from statements.verify_account_base import VerifyAccountStatementsBase


class VerifyAccountStatements(VerifyAccountStatementsBase):
    """Scenario 3.1: Correct code activates the account, and what a bad request gets."""

    MALFORMED_CODE = "12345"
    MALFORMED_EMAIL = "not-an-email"
    WRONG_CODE = "999999"
    UNKNOWN_EMAIL = "nobody@example.ru"
    INVALID_OR_EXPIRED_MESSAGE = "The verification code is invalid or has expired."
    INVALID_CODE_MESSAGE = "The verification code is not valid."

    async def given_account_with_no_verification_code_ever_issued(self) -> None:
        """An account row with nothing in the code repository behind it.

        Reachable: registration writes the account and the code in that order, so
        a failure between the two -- or any later cleanup of codes -- leaves this
        state. It is the one branch in VerifyAccount that no test reached.
        """
        account = Account.create(
            id=uuid4(),
            email="user@example.ru",
            password_hash="hash",
            created_at=self.FIXED_CLOCK_NOW,
        )
        await self.account_repository.save(account)
        self.registered_email = account.email

    async def verify_an_account_that_has_no_code(self) -> None:
        await self._execute_verify(self.registered_email, "123456")

    def assert_rejected_as_invalid_or_expired_with_no_code_to_look_at(self) -> None:
        """The account exists, the lookup ran, and the answer is still generic.

        A separate assertion from `assert_rejected_as_invalid_or_expired` because
        that one requires a code to have been issued -- and the whole premise here
        is that none was. The lookup count is what pins the branch: without it the
        test would pass even if the account had not been found, which is a
        different branch that answers the same way on purpose.
        """
        self._assert_validation_exception(
            "INVALID_OR_EXPIRED_CODE", self.INVALID_OR_EXPIRED_MESSAGE
        )
        assert self.verification_code_repository.find_active_by_account_id_call_count == 1, (
            "expected the account to be found and its code looked up exactly once, got "
            f"{self.verification_code_repository.find_active_by_account_id_call_count} call(s)"
        )
        assert self.account_repository.saved_accounts[0].is_verified is False, (
            "expected the account to stay unverified"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected no commit, got {self.unit_of_work.commit_call_count}"
        )

    async def verify_with_the_issued_code(self) -> None:
        await self._execute_verify(self.registered_email, self.issued_code)

    async def verify_with_a_malformed_code(self) -> None:
        await self._execute_verify(self.registered_email, self.MALFORMED_CODE)

    async def verify_with_a_malformed_email(self) -> None:
        await self._execute_verify(self.MALFORMED_EMAIL, self.issued_code)

    async def verify_with_both_a_malformed_email_and_a_malformed_code(self) -> None:
        # The only statement that varies both axes at once. Every other one holds
        # one valid, so they all stay green under either validation order -- this
        # is what actually pins the ADR's email-first decision.
        await self._execute_verify(self.MALFORMED_EMAIL, self.MALFORMED_CODE)

    async def verify_with_a_wrong_but_well_formed_code(self) -> None:
        await self._execute_verify(self.registered_email, self.WRONG_CODE)

    async def verify_with_an_unknown_email(self) -> None:
        await self._execute_verify(self.UNKNOWN_EMAIL, self.issued_code)

    async def verify_with_the_issued_code_after_it_expired(self) -> None:
        # The code expires 10 minutes after issuance; step exactly onto the expiry
        # instant, which auth_verify.yaml treats as already expired.
        self.clock.fixed_now = self.FIXED_CLOCK_NOW + timedelta(minutes=10)
        await self.verify_with_the_issued_code()

    def assert_rejected_as_invalid_code_without_touching_repositories(self) -> None:
        self._assert_validation_exception("INVALID_CODE", self.INVALID_CODE_MESSAGE)
        assert self.account_repository.find_by_email_call_count == 0, (
            f"expected a malformed code to be rejected before any account lookup, "
            f"got {self.account_repository.find_by_email_call_count} find_by_email call(s)"
        )
        assert self.verification_code_repository.find_active_by_account_id_call_count == 0, (
            f"expected a malformed code to be rejected before any verification-code lookup, got "
            f"{self.verification_code_repository.find_active_by_account_id_call_count} call(s)"
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected no Account write on the malformed-code path (only the register-time "
            f"save), got {len(self.account_repository.saved_accounts)} saves"
        )

    def assert_rejected_as_invalid_email(self) -> None:
        self._assert_validation_exception("INVALID_EMAIL", self.INVALID_EMAIL_MESSAGE)

    def assert_rejected_as_invalid_email_not_invalid_code(self) -> None:
        # Pins the ADR's validation-ordering decision (email before code) against a
        # request that is bad on both axes -- the one input where the order is
        # observable at all.
        self._assert_validation_exception("INVALID_EMAIL", self.INVALID_EMAIL_MESSAGE)

    def assert_account_is_verified(self) -> None:
        assert self.thrown_exception is None, (
            f"expected no exception to be raised, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected the Account to be written once (at register); verify now transitions "
            f"it in place via the atomic conditional UPDATE (transition_to_verified), not a "
            f"second save, got {len(self.account_repository.saved_accounts)} saves"
        )
        original = self.original_account_snapshot
        verified_account = self.account_repository.saved_accounts[-1]
        actual_unchanged = {
            field: getattr(verified_account, field) for field in self.UNCHANGED_BY_VERIFY_FIELDS
        }
        expected_unchanged = {field: original[field] for field in self.UNCHANGED_BY_VERIFY_FIELDS}
        assert actual_unchanged == expected_unchanged, (
            f"expected verify to leave every field but is_verified unchanged, "
            f"got {actual_unchanged} vs original {expected_unchanged}"
        )
        assert original["is_verified"] is False, (
            f"expected the Account to be unverified immediately after registration, "
            f"got {original['is_verified']}"
        )
        assert verified_account.is_verified is True, (
            f"expected the persisted Account.is_verified to be True after verification, "
            f"got {verified_account.is_verified}"
        )
        verified_code = self.verification_code_repository.saved_codes[-1]
        assert verified_code.consumed_at == self.FIXED_CLOCK_NOW, (
            f"expected the matched VerificationCode.consumed_at to be set to the clock's "
            f"current time on successful verification, got {verified_code.consumed_at}"
        )
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected unit_of_work.commit() to be called exactly once, "
            f"got {self.unit_of_work.commit_call_count}"
        )

    def assert_rejected_as_invalid_or_expired(self) -> None:
        """One generic rejection, and no state change.

        The error code is asserted identical for a wrong code, an unknown email
        and an expired code -- that sameness is the point, since a distinct code
        (or a 500 from a None dereference) would reveal whether the email exists.
        """
        self._assert_validation_exception(
            "INVALID_OR_EXPIRED_CODE", self.INVALID_OR_EXPIRED_MESSAGE
        )
        assert len(self.account_repository.saved_accounts) == 1, (
            f"expected no Account write on a rejected verify (only the register-time save), "
            f"got {len(self.account_repository.saved_accounts)} saves"
        )
        assert self.account_repository.saved_accounts[0].is_verified is False, (
            "expected the account to stay unverified after a rejected verify"
        )
        assert len(self.verification_code_repository.saved_codes) == 1, (
            f"expected no VerificationCode write on a rejected verify, "
            f"got {len(self.verification_code_repository.saved_codes)} saves"
        )
        assert self.verification_code_repository.saved_codes[0].consumed_at is None, (
            "expected the code to stay unconsumed after a rejected verify -- a consumed "
            "code could never be retried"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected no commit on a rejected verify, got {self.unit_of_work.commit_call_count}"
        )
