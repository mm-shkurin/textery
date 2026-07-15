from typing import Optional


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commit_call_count = 0
        self.rollback_call_count = 0
        self.raise_on_commit: Optional[Exception] = None

    async def commit(self) -> None:
        if self.raise_on_commit is not None:
            raise self.raise_on_commit
        self.commit_call_count += 1

    async def rollback(self) -> None:
        self.rollback_call_count += 1
