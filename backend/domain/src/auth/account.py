from datetime import datetime
from typing import Any
from uuid import UUID


class Account:
    """Domain entity for a registered account.

    is_verified is never a constructor parameter: it is always False when
    an Account is created. There is no public setter, so no code path
    (including caller-supplied request data) can flip it to True at
    creation time.
    """

    def __init__(self, id: UUID, email: str, password_hash: str, created_at: datetime) -> None:
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.is_verified = False

    @classmethod
    def create(cls, id: UUID, email: str, password_hash: str, clock: Any) -> "Account":
        return cls(
            id=id,
            email=email,
            password_hash=password_hash,
            created_at=clock.now(),
        )
