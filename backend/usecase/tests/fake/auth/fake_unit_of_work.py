

class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commit_call_count = 0
        self.rollback_call_count = 0
        self.raise_on_commit: Exception | None = None
        self.raise_on_rollback: Exception | None = None

    async def commit(self) -> None:
        if self.raise_on_commit is not None:
            raise self.raise_on_commit
        self.commit_call_count += 1

    async def rollback(self) -> None:
        self.rollback_call_count += 1
        if self.raise_on_rollback is not None:
            raise self.raise_on_rollback
