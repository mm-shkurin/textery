from statements.verify_account_base import VerifyAccountStatementsBase


class VerifyAccountAlreadyVerifiedStatements(VerifyAccountStatementsBase):
    """Scenario 3.5: verifying against an already-verified account with any code
    that is NOT the one that verified it is rejected with ALREADY_VERIFIED.

    Reached by first verifying the account normally (like 3.4's setup), then
    submitting a DIFFERENT valid-shape 6-digit code. The invariant is asserted
    NEGATIVELY (see the ADR
    `decisions/verify-idempotent-and-already-verified-decision.md`, section
    "Guarantee the tests must pin"): the rejection must persist nothing -- no
    Account save, no VerificationCode save, no commit -- so the save/commit
    baselines are captured after the FIRST verify and must be unchanged after the
    rejected call.
    """

    ALREADY_VERIFIED_ERROR_CODE = "ALREADY_VERIFIED"
    ALREADY_VERIFIED_MESSAGE = "The account is already verified."

    def _a_non_matching_code(self) -> str:
        # Flip the last digit so the code is guaranteed to differ from the one that
        # verified the account while staying a valid 6-digit shape (so it is not
        # rejected as INVALID_CODE before the is_verified fork is even reached).
        last_digit = int(self.issued_code[-1])
        return self.issued_code[:-1] + str((last_digit + 1) % 10)

    async def submit_a_different_code_against_the_verified_account(self) -> None:
        different_code = self._a_non_matching_code()
        assert different_code != self.issued_code, (
            f"setup sanity: the derived code {different_code} must differ from the "
            f"issued code {self.issued_code}"
        )
        await self._execute_verify(self.registered_email, different_code)

    def assert_rejected_as_already_verified_without_persisting(self) -> None:
        self._assert_validation_exception(
            self.ALREADY_VERIFIED_ERROR_CODE, self.ALREADY_VERIFIED_MESSAGE
        )
        assert (
            len(self.account_repository.saved_accounts) == self.account_saves_after_first_verify
        ), (
            f"expected NO Account persist on the rejected verify, so the save count "
            f"stays {self.account_saves_after_first_verify}, got "
            f"{len(self.account_repository.saved_accounts)}"
        )
        assert (
            len(self.verification_code_repository.saved_codes) == self.code_saves_after_first_verify
        ), (
            f"expected NO VerificationCode persist on the rejected verify, so the save "
            f"count stays {self.code_saves_after_first_verify}, got "
            f"{len(self.verification_code_repository.saved_codes)}"
        )
        assert self.unit_of_work.commit_call_count == self.commits_after_first_verify, (
            f"expected NO commit on the rejected verify, so the commit count stays "
            f"{self.commits_after_first_verify}, got {self.unit_of_work.commit_call_count}"
        )
