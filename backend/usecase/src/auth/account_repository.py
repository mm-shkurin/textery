from typing import Optional, Protocol
from uuid import UUID

from auth.account import Account


class AccountRepository(Protocol):
    async def save(self, account: Account) -> None:
        ...

    async def find_by_email(self, email: str) -> Optional[Account]:
        ...

    async def find_by_id(self, account_id: UUID) -> Optional[Account]:
        ...
