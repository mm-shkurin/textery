from auth.account import Account


class FakeAccountRepository:
    def __init__(self) -> None:
        self.saved_accounts: list[Account] = []

    async def save(self, account: Account) -> None:
        self.saved_accounts.append(account)
