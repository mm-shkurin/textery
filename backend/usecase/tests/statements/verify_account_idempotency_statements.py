from datetime import timedelta

from statements.verify_account_base import VerifyAccountStatementsBase


class VerifyAccountIdempotencyStatements(VerifyAccountStatementsBase):
    """Scenario 3.4: re-submitting an already-consumed code is a genuine no-op.

    The invariant is asserted NEGATIVELY (see the ADR
    `decisions/verify-idempotent-and-already-verified-decision.md`, section
    "Guarantee the tests must pin"): a replay must not persist a second time and
    must not overwrite the first consume time. A guard that merely counts that
    calls happened goes green on the current buggy `save`==2/`commit`==2 tail --
    so the baseline is captured after the FIRST verify and the replay must leave
    every count and `consumed_at` exactly where the first verify left them.
    """

    # One minute past issuance: still inside the 10-minute validity window (so the
    # replay is not rejected as expired), but distinct from the first consume time
    # so an overwrite of consumed_at would be detectable.
    REPLAY_CLOCK_NOW = VerifyAccountStatementsBase.FIXED_CLOCK_NOW + timedelta(minutes=1)

    def __init__(self) -> None:
        super().__init__()
        self.first_consumed_at = None
        self.account_saves_after_first_verify = 0
        self.code_saves_after_first_verify = 0
        self.commits_after_first_verify = 0

    async def given_account_already_verified_once_with_its_code(self) -> None:
        await self.given_pending_account_with_verification_code()
        await self._execute_verify(self.registered_email, self.issued_code)
        # Snapshot the FIRST consume time as a value (datetime is immutable): the
        # Fake shares object identity across saves, so a later re-consume would
        # otherwise mutate this in place and hide the overwrite.
        self.first_consumed_at = self.verification_code_repository.saved_codes[-1].consumed_at
        self.account_saves_after_first_verify = len(self.account_repository.saved_accounts)
        self.code_saves_after_first_verify = len(self.verification_code_repository.saved_codes)
        self.commits_after_first_verify = self.unit_of_work.commit_call_count

    async def resubmit_the_same_already_consumed_code(self) -> None:
        # Advance the clock so any re-consume would stamp a DIFFERENT time than the
        # first one -- the whole point of the negative consumed_at assertion.
        self.clock.fixed_now = self.REPLAY_CLOCK_NOW
        await self._execute_verify(self.registered_email, self.issued_code)

    def assert_replay_was_a_no_op(self) -> None:
        assert self.thrown_exception is None, (
            f"expected the idempotent replay to succeed silently, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert self.first_consumed_at == self.FIXED_CLOCK_NOW, (
            f"setup sanity: expected the first verify to consume the code at the "
            f"original clock time, got {self.first_consumed_at}"
        )
        assert (
            len(self.verification_code_repository.saved_codes)
            == self.code_saves_after_first_verify
        ), (
            f"expected NO second VerificationCode persist on replay, so the save "
            f"count stays {self.code_saves_after_first_verify}, got "
            f"{len(self.verification_code_repository.saved_codes)}"
        )
        assert (
            len(self.account_repository.saved_accounts)
            == self.account_saves_after_first_verify
        ), (
            f"expected NO second Account persist on replay, so the save count stays "
            f"{self.account_saves_after_first_verify}, got "
            f"{len(self.account_repository.saved_accounts)}"
        )
        assert self.unit_of_work.commit_call_count == self.commits_after_first_verify, (
            f"expected NO second commit on replay, so the commit count stays "
            f"{self.commits_after_first_verify}, got {self.unit_of_work.commit_call_count}"
        )
        assert (
            self.verification_code_repository.saved_codes[-1].consumed_at
            == self.first_consumed_at
        ), (
            f"expected the stored code's consumed_at to stay the FIRST consume time "
            f"{self.first_consumed_at} (no re-consume), got "
            f"{self.verification_code_repository.saved_codes[-1].consumed_at}"
        )
