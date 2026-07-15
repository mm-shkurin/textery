from typing import Optional

from auth.account import Account


class FakeAccountRepository:
    def __init__(self) -> None:
        self.saved_accounts: list[Account] = []
        self.raise_on_save: Optional[Exception] = None

    async def save(self, account: Account) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_accounts.append(account)
