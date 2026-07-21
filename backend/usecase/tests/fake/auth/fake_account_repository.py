from uuid import UUID

from auth.account import Account


class FakeAccountRepository:
    def __init__(self) -> None:
        self.saved_accounts: list[Account] = []
        self.raise_on_save: Exception | None = None
        self.find_by_email_call_count = 0
        self.transition_to_verified_calls: list[UUID] = []
        self.lock_for_update_calls: list[UUID] = []
        # Scenario 5.3: spy on the atomic failed-attempt increment so a usecase
        # test can assert the wrong-password branch calls it with the account id.
        self.increment_failed_attempts_calls: list[UUID] = []
        # Shared across the two Fakes so a test can assert the RELATIVE order of
        # lock_for_update vs the cooldown read (find_active_by_account_id). Left None
        # by default so existing Statements pay no cost; a test opts in by assigning
        # the same list to both Fakes' call_log.
        self.call_log: list[str] | None = None
        # premortem #2 lever: when enabled, lock_for_update RE-READS a DIFFERENT
        # account than find_by_email returned (mirrors the real SELECT ... FOR UPDATE
        # re-read), so a test can prove ResendCode threads the POST-lock account
        # forward rather than the stale pre-lock one.
        self.lock_for_update_override_enabled = False
        self.lock_for_update_result: Account | None = None

    async def save(self, account: Account) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_accounts.append(account)

    async def find_by_email(self, email: str) -> Account | None:
        self.find_by_email_call_count += 1
        return next((a for a in reversed(self.saved_accounts) if a.email == email), None)

    async def find_by_id(self, account_id: UUID) -> Account | None:
        return next((a for a in reversed(self.saved_accounts) if a.id == account_id), None)

    async def lock_for_update(self, account_id: UUID) -> Account | None:
        # Spy: records the id it was locked with and its position relative to the
        # cooldown read. The Fake does NOT serialize (single-threaded) -- real
        # serialization is a db property proven by the db-adapter race test; this
        # only pins the usecase call-site. Returns the re-read locked account (the
        # override lets a test hand back a DIFFERENT account than find_by_email).
        self.lock_for_update_calls.append(account_id)
        if self.call_log is not None:
            self.call_log.append("lock_for_update")
        if self.lock_for_update_override_enabled:
            return self.lock_for_update_result
        return await self.find_by_id(account_id)

    async def increment_failed_attempts(self, account_id: UUID) -> None:
        # Spy + real semantics mirroring the db adapter's single atomic
        # UPDATE ... SET count = count + 1. The recorded id is what the usecase
        # test asserts on, and call_log (when shared) pins increment-before-commit
        # ordering. A regression that stops calling this leaves the list empty ->
        # RED.
        self.increment_failed_attempts_calls.append(account_id)
        if self.call_log is not None:
            self.call_log.append("increment_failed_attempts")

    async def transition_to_verified(self, account_id: UUID) -> bool:
        # Spy + real semantics, mirroring the atomic conditional UPDATE the db
        # adapter runs: the first caller flips is_verified false->true and gets
        # True; a later caller (the race loser, or a replay) finds the row already
        # verified and gets False with no mutation. The recorded id is what the
        # usecase test asserts on, so a regression back to verify()+save() -- which
        # never touches this method -- leaves the list empty and goes RED.
        self.transition_to_verified_calls.append(account_id)
        account = await self.find_by_id(account_id)
        if account is None or account.is_verified:
            return False
        account.verify()
        return True
