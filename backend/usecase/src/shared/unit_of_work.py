from typing import Protocol


class UnitOfWork(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class NullUnitOfWork:
    """No-op UnitOfWork used when a usecase is constructed without one."""

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None
