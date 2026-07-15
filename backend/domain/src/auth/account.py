from datetime import datetime
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
        self._is_verified = False

    @property
    def is_verified(self) -> bool:
        return self._is_verified

    @classmethod
    def create(cls, id: UUID, email: str, password_hash: str, created_at: datetime) -> "Account":
        return cls(
            id=id,
            email=email,
            password_hash=password_hash,
            created_at=created_at,
        )

    @classmethod
    def reconstitute(
        cls, id: UUID, email: str, password_hash: str, created_at: datetime, is_verified: bool
    ) -> "Account":
        account = cls(
            id=id,
            email=email,
            password_hash=password_hash,
            created_at=created_at,
        )
        account._is_verified = is_verified
        return account

    def verify(self) -> None:
        self._is_verified = True
