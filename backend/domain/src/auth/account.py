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
        self._failed_attempt_count = 0
        # Not a constructor parameter, for the same reason is_verified is not: a
        # newly registered account has no display name, and registration never
        # accepts one. It arrives only through rename().
        self._name: str | None = None

    @property
    def name(self) -> str | None:
        """The display name, or None when the account has none.

        None is a value, not an absence to be papered over: the read contract
        always emits the `name` key and emits `null` here, and the header uses
        that to choose its email fallback. Never normalize this to `''`.
        """
        return self._name

    def rename(self, name: str | None) -> None:
        """Set or clear the display name.

        Takes an already-normalized value (`AccountName.value`), not raw input:
        the entity applies the change, the value object decides what the change
        is. `None` clears -- there is no separate clear() operation, because to
        the contract clearing IS a rename to nothing.
        """
        self._name = name

    @property
    def is_verified(self) -> bool:
        return self._is_verified

    @property
    def failed_attempt_count(self) -> int:
        return self._failed_attempt_count

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
        cls,
        id: UUID,
        email: str,
        password_hash: str,
        created_at: datetime,
        is_verified: bool,
        failed_attempt_count: int = 0,
        name: str | None = None,
    ) -> "Account":
        account = cls(
            id=id,
            email=email,
            password_hash=password_hash,
            created_at=created_at,
        )
        account._is_verified = is_verified
        account._failed_attempt_count = failed_attempt_count
        account._name = name
        return account

    def verify(self) -> None:
        self._is_verified = True
