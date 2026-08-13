from datetime import UTC, datetime

from pydantic import BaseModel, ValidationInfo, field_validator

from auth.account import Account


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

    @field_validator("created_at")
    @classmethod
    def _as_utc(cls, value: datetime, info: ValidationInfo) -> datetime:
        """Convert to UTC, refusing a naive value rather than guessing its zone.

        The same rule `ProjectItemDto._as_utc` applies, and for the same reason:
        `astimezone(UTC)` does not raise on a naive datetime, it reads it as the
        HOST's local time. That turns a visible violation -- an offset-less string
        -- into an invisible one: a well-formed `Z` naming the wrong instant,
        correct inside a UTC container and silently shifted on a developer machine.
        """
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def from_domain(cls, account: Account) -> "ProfileResponseDto":
        return cls(email=account.email, name=account.name, created_at=account.created_at)
