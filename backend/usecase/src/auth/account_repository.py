from typing import Protocol

from auth.account import Account


class AccountRepository(Protocol):
    async def save(self, account: Account) -> None:
        ...
