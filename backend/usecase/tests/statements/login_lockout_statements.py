from uuid import uuid4

from scope.register_request_scope import RegisterRequestScope
from statements.login_failed_attempt_statements import LoginFailedAttemptStatements

from auth.account import Account


class LoginLockoutStatements(LoginFailedAttemptStatements):
    """Scenario 5.4: an account locks out after N consecutive failed attempts.

    Once `failed_attempt_count >= LOCKOUT_THRESHOLD` the login is rejected with a
    distinct 403 `ACCOUNT_LOCKED` -- BEFORE the password is even checked, so even a
    correct password is refused. A successful login below the threshold must RESET
    the counter to zero and COMMIT that reset (the happy path has a UoW wired since
    5.3 but never commits -- a reset UPDATE without commit is silently rolled back).

    Reuses LoginFailedAttemptStatements' UoW-wired login runner and the shared
    call_log so reset -> commit ordering is assertable.
    """

    LOCKOUT_THRESHOLD = 5
    KNOWN_PASSWORD = RegisterRequestScope.DEFAULTS["password"]
    ACCOUNT_LOCKED_MESSAGE = "This account is temporarily locked due to repeated failed logins."

    async def _given_verified_account_with_count(self, count: int) -> None:
        # Built directly via reconstitute (not through RegisterUser) so the account
        # can carry a pre-existing failed_attempt_count -- registration always starts
        # at zero, and this scenario needs an account already at or below the gate.
        account = Account.reconstitute(
            id=uuid4(),
            email="locked@example.ru",
            password_hash=self.password_hasher.hash(self.KNOWN_PASSWORD),
            created_at=self.FIXED_CLOCK_NOW,
            is_verified=True,
            failed_attempt_count=count,
        )
        await self.account_repository.save(account)
        self.account_email = account.email
        self.account_id = account.id
        self.account_password = self.KNOWN_PASSWORD

    async def given_verified_account_at_the_lockout_threshold(self) -> None:
        await self._given_verified_account_with_count(self.LOCKOUT_THRESHOLD)

    async def given_verified_account_one_below_the_lockout_threshold(self) -> None:
        await self._given_verified_account_with_count(self.LOCKOUT_THRESHOLD - 1)

    def assert_rejected_as_locked_without_verifying_or_issuing(self) -> None:
        # The gate runs BEFORE password verification: a locked account is refused
        # with the distinct 403 code, no token is minted, and verify() is never
        # reached (so a correct password cannot slip through).
        self._assert_validation_exception("ACCOUNT_LOCKED", self.ACCOUNT_LOCKED_MESSAGE)
        assert self.token_service.issued_for == [], (
            f"expected no token pair to be issued for a locked account, "
            f"got {self.token_service.issued_for}"
        )
        assert self.password_hasher.verify_call_count == 0, (
            f"expected the lockout gate to short-circuit BEFORE password "
            f"verification, but verify() was called "
            f"{self.password_hasher.verify_call_count} time(s)"
        )

    def _assert_reset_attempted_once(self) -> None:
        # Exactly one atomic reset for the authenticated account. Shared by the
        # committed-happy-path guard and the commit-fails coverage branch (which
        # cannot reuse the full committed guard: commit_call_count is 0 there).
        assert self.account_repository.reset_failed_attempts_calls == [self.account_id], (
            f"expected exactly one atomic reset for the authenticated account "
            f"{self.account_id}, got "
            f"{self.account_repository.reset_failed_attempts_calls}"
        )

    def _assert_reset_committed_once(self) -> None:
        # Shared strict guard: exactly one atomic reset for the authenticated account
        # AND exactly one commit to persist it (a reset that never commits is silently
        # rolled back on session.close() -- 5.3 premortem carry).
        self._assert_reset_attempted_once()
        assert self.unit_of_work.commit_call_count == 1, (
            f"expected exactly one commit to persist the reset, got "
            f"{self.unit_of_work.commit_call_count}"
        )

    def assert_authenticated_and_reset_the_counter(self) -> None:
        # Below the threshold the correct password authenticates AND the counter is
        # reset then committed -- reset must precede commit or the UPDATE is lost.
        self.assert_token_pair_issued_for_the_account()
        self._assert_reset_committed_once()
        assert self.call_log == ["reset_failed_attempts", "commit"], (
            f"expected the counter to be reset then committed on the happy path, "
            f"got call order {self.call_log}"
        )

    def assert_committed_the_reset(self) -> None:
        # Focused commit guard (5.3 premortem carry): pin the reset+commit explicitly
        # so a reset-without-commit implementation goes RED, not silently green.
        self._assert_reset_committed_once()

    async def login_with_the_correct_password_while_the_reset_commit_fails(self) -> None:
        # Coverage 5.4: a stale failed-attempt count must NEVER block a valid login
        # (ADR §4). Arm the shared UoW to blow up on the reset's commit, then drive
        # the SUCCESS/reset branch (not the wrong-password branch 5.3 covers).
        self.unit_of_work.raise_on_commit = RuntimeError("commit failed")
        await self.login_with_the_correct_password()

    def assert_authenticated_despite_the_failed_reset_commit(self) -> None:
        # The swallow lets the login proceed: the token pair is still issued (no
        # exception surfaces to the client), the reset was attempted, the commit was
        # attempted, and the poisoned txn was rolled back quietly.
        self.assert_token_pair_issued_for_the_account()
        self._assert_reset_attempted_once()
        assert self.unit_of_work.commit_attempt_count == 1, (
            f"expected exactly one commit attempt to persist the reset, got "
            f"{self.unit_of_work.commit_attempt_count}"
        )
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected exactly one rollback after the reset commit failed, got "
            f"{self.unit_of_work.rollback_call_count}"
        )
