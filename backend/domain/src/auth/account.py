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
        # The INSTANT the avatar last changed -- never the avatar itself. The
        # bytes are deliberately not a field on this entity: an attribute here is
        # an attribute `AccountModel.to_domain` has to read, and reading it would
        # pull hundreds of kilobytes of `bytea` into every profile read, which is
        # the product's highest-rate query. The image is loaded only by the route
        # that serves it, through its own repository method.
        self._avatar_updated_at: datetime | None = None

    @property
    def avatar_updated_at(self) -> datetime | None:
        """When the avatar last changed, or None when there is none.

        This is what `GET /me` reports, and it is the whole of what a client needs
        to know without fetching the image: it decides whether to request the
        bytes at all, and doubles as the cache-buster on the URL when it does.
        """
        return self._avatar_updated_at

    def set_avatar_updated_at(self, updated_at: datetime | None) -> None:
        """Record that the avatar changed at `updated_at`, or was removed (None).

        The entity tracks only WHEN, never the image: the bytes are written and
        read by their own repository, so they never pass through here. `None` is
        the removal, which is why this is one method and not a set/clear pair --
        to a client, an avatar that is gone and an account that never had one are
        the same state.
        """
        self._avatar_updated_at = updated_at

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
        avatar_updated_at: datetime | None = None,
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
        account._avatar_updated_at = avatar_updated_at
        return account

    def verify(self) -> None:
        self._is_verified = True
