from shared.exceptions import VerificationFailedException
from statements.verify_account_base import VerifyAccountStatementsBase


class VerifyAccountFailureStatements(VerifyAccountStatementsBase):
    """What /verify does when the write itself fails, rather than the request.

    A separate class from VerifyAccountStatements because it asks a different
    question: those tests are about which answer a bad request gets, these are
    about not leaking driver detail — and not letting a failing rollback replace
    the exception that explains what actually went wrong. Same reason
    register_atomic_write_statements is separate from register_statements.
    """

    VERIFICATION_FAILED_MESSAGE = (
        "Verification could not be completed due to an unexpected error. Please try again."
    )

    async def verify_with_the_issued_code_when_final_commit_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError("connection reset")
        await self._execute_verify(self.account_email, self.account_code)

    async def verify_with_the_issued_code_when_rollback_itself_fails(self) -> None:
        self.unit_of_work.raise_on_commit = RuntimeError("connection reset")
        self.unit_of_work.raise_on_rollback = RuntimeError("rollback also failed")
        await self._execute_verify(self.account_email, self.account_code)

    def assert_verification_failed_and_rolled_back(self) -> None:
        self._assert_verification_failed_with_sanitized_message()
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected unit_of_work.rollback() to be called exactly once on commit failure, "
            f"got {self.unit_of_work.rollback_call_count}"
        )

    def assert_verification_failed_when_rollback_also_fails(self) -> None:
        self._assert_verification_failed_with_sanitized_message()
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected unit_of_work.rollback() to be attempted exactly once even when it "
            f"raises, got {self.unit_of_work.rollback_call_count}"
        )

    def _assert_verification_failed_with_sanitized_message(self) -> None:
        assert isinstance(self.thrown_exception, VerificationFailedException), (
            f"expected VerificationFailedException, got "
            f"{type(self.thrown_exception).__name__ if self.thrown_exception else None}: "
            f"{self.thrown_exception}"
        )
        # Exact equality is what proves sanitization: a message equal to the
        # client-safe constant cannot carry any driver/rollback failure detail.
        assert self.thrown_exception.message == self.VERIFICATION_FAILED_MESSAGE, (
            f"expected the client-safe message '{self.VERIFICATION_FAILED_MESSAGE}', "
            f"got '{self.thrown_exception.message}'"
        )
        assert str(self.thrown_exception) == self.VERIFICATION_FAILED_MESSAGE, (
            f"expected str(exception) to carry only the client-safe message, "
            f"got '{self.thrown_exception}'"
        )
