from uuid import UUID

from auth.account import Account


class FakeAccountRepository:
    def __init__(self) -> None:
        self.saved_accounts: list[Account] = []
        self.raise_on_save: Exception | None = None
        self.find_by_email_call_count = 0
        self.transition_to_verified_calls: list[UUID] = []

    async def save(self, account: Account) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_accounts.append(account)

    async def find_by_email(self, email: str) -> Account | None:
        self.find_by_email_call_count += 1
        return next((a for a in reversed(self.saved_accounts) if a.email == email), None)

    async def find_by_id(self, account_id: UUID) -> Account | None:
        return next((a for a in reversed(self.saved_accounts) if a.id == account_id), None)

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
