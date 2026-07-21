from statements.login_statements import LoginStatements

from auth.login_user import LoginUser


class LoginFailedAttemptStatements(LoginStatements):
    """Scenario 5.3: a wrong password on a FOUND account is counted atomically.

    The wrong-password branch must increment the failed-attempt counter and
    commit it BEFORE raising the generic INVALID_CREDENTIALS (5.2) -- the count
    must survive even though the login fails. The two non-failure branches must
    NOT increment: an unknown email has no row to touch, and a correct password
    on an unverified account is not a failed attempt (the password was right).

    Overrides the base login runner to construct LoginUser WITH the UnitOfWork
    and to share one call_log across the repo and the UoW, so the test can pin
    increment -> commit ordering.
    """

    def __init__(self) -> None:
        super().__init__()
        self.call_log: list[str] = []
        self.account_repository.call_log = self.call_log
        self.unit_of_work.call_log = self.call_log

    async def _execute_login(self, email: str, password: str) -> None:
        # Measure only the login action. The given* setup verifies the account via
        # VerifyAccount, which commits on this same shared UnitOfWork -- reset the
        # spies so a stray setup commit is not counted against the login branch.
        self.unit_of_work.commit_call_count = 0
        self.account_repository.increment_failed_attempts_calls.clear()
        self.call_log.clear()
        try:
            self.issued_pair = await LoginUser(
                account_repository=self.account_repository,
                password_hasher=self.password_hasher,
                token_service=self.token_service,
                unit_of_work=self.unit_of_work,
            ).execute(email=email, password=password)
        except Exception as exc:
            self.thrown_exception = exc

    def assert_counted_the_failed_attempt_then_rejected(self) -> None:
        assert self.account_repository.increment_failed_attempts_calls == [self.account_id], (
            f"expected exactly one atomic increment for the found account "
            f"{self.account_id}, got "
            f"{self.account_repository.increment_failed_attempts_calls}"
        )
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected exactly one commit to persist the failed attempt, got "
            f"{self.unit_of_work.commit_call_count}"
        )
        assert self.call_log == ["increment_failed_attempts", "commit"], (
            f"expected the counter to be incremented then committed BEFORE the "
            f"raise, got call order {self.call_log}"
        )
        # The 401 contract (INVALID_CREDENTIALS + no token minted) is unchanged
        # from 5.2 -- reuse the base assertion rather than re-encoding it.
        self.assert_rejected_as_invalid_credentials()

    def assert_did_not_count_any_attempt(self) -> None:
        assert self.account_repository.increment_failed_attempts_calls == [], (
            f"expected no failed-attempt increment on this branch, got "
            f"{self.account_repository.increment_failed_attempts_calls}"
        )
        assert self.unit_of_work.commit_call_count == 0, (
            f"expected no commit on a branch that writes nothing, got "
            f"{self.unit_of_work.commit_call_count}"
        )
