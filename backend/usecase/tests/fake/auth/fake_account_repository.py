from typing import Optional

from auth.account import Account


class FakeAccountRepository:
    def __init__(self) -> None:
        self.saved_accounts: list[Account] = []
        self.raise_on_save: Optional[Exception] = None
        self.find_by_email_call_count = 0

    async def save(self, account: Account) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_accounts.append(account)

    async def find_by_email(self, email: str) -> Optional[Account]:
        self.find_by_email_call_count += 1
        for account in reversed(self.saved_accounts):
            if account.email == email:
                return account
        return None
