from datetime import UTC, datetime

from pydantic import BaseModel, ValidationInfo, field_validator

from auth.account import Account
from auth.deletion_confirmation import has_password


class ProfileResponseDto(BaseModel):
    """The `/api/v1/auth/me` body, for both the GET and the PATCH.

    One DTO for both operations because PATCH answers with the whole profile: the
    client updates its identity snapshot from the response it already has, with no
    re-GET, and a second shape here would let the two drift.

    `name` is `str | None` and is ALWAYS emitted, `null` when unset. Not optional,
    not omitted: the header decides between the display name and its email
    fallback on this key, and a client that has to distinguish "absent" from
    "null" is a client the contract failed to describe.

    `is_verified` is deliberately absent. Only a verified account can log in, so
    the field would be the constant `true` on every response this route can
    produce -- a field whose value is a tautology invites a client to branch on it.

    `password_hash` and `failed_attempt_count` are likewise absent, and that is
    enforced by listing fields rather than dumping the entity: Pydantic serializes
    exactly what is declared here, so a future column on `Account` cannot leak by
    being added.
    """

    email: str
    name: str | None
    created_at: datetime
    # ALWAYS emitted, `null` when the account has no avatar -- the same rule
    # `name` follows, and for a sharper reason: this key is how a client decides
    # whether to request the image at all, and it is the cache-buster it puts on
    # the URL when it does. Omitting it on the no-avatar case would leave the
    # client unable to tell "no avatar" from "this response does not say".
    #
    # The IMAGE is not here and must never be. `GET /me` runs on every
    # authenticated page view; a base64 image inline would add hundreds of
    # kilobytes to the product's highest-rate response.
    avatar_updated_at: datetime | None
    # Which confirmation the deletion endpoint will accept from THIS account, and
    # the only way the client can know it. An OAuth-only account is created with
    # `password_hash=""` (complete_oauth_callback.py), so it can never be confirmed
    # by password; an account that has one can never be confirmed by address,
    # because the deletion screen displays that address and the gate would reduce
    # to reading it.
    #
    # Emitted rather than inferred client-side because there is nothing to infer
    # from: the hash is not on the wire and must not be. Without this key the
    # client falls back to the address form for everyone, and every password
    # account is then refused on a form that has no alternative on screen --
    # deletion becomes impossible for them, which is what shipped before this
    # field existed.
    #
    # It discloses nothing an attacker with a session does not already have: the
    # account is theirs, and the sign-in screen already reveals which methods an
    # address supports.
    has_password: bool

    @field_validator("created_at", "avatar_updated_at")
    @classmethod
    def _as_utc(cls, value: datetime | None, info: ValidationInfo) -> datetime | None:
        """Convert to UTC, refusing a naive value rather than guessing its zone.

        The same rule `ProjectItemDto._as_utc` applies, and for the same reason:
        `astimezone(UTC)` does not raise on a naive datetime, it reads it as the
        HOST's local time. That turns a visible violation -- an offset-less string
        -- into an invisible one: a well-formed `Z` naming the wrong instant,
        correct inside a UTC container and silently shifted on a developer machine.
        """
        # None is the absent avatar, not a violation -- it passes through
        # untouched. Only a present instant has a zone to be wrong about.
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def from_domain(cls, account: Account) -> "ProfileResponseDto":
        return cls(
            email=account.email,
            name=account.name,
            created_at=account.created_at,
            avatar_updated_at=account.avatar_updated_at,
            has_password=has_password(account),
        )
