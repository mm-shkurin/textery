import secrets
from datetime import datetime, timedelta

STATE_BYTES = 32
STATE_TTL_MINUTES = 10


class OAuthState:
    """The CSRF state minted at /start and consumed once at /callback.

    Server-minted and server-stored: a state the client could produce or predict
    would let an attacker deliver a callback of their own choosing and have it
    accepted as a legitimate leg of somebody else's sign-in.
    """

    def __init__(
        self,
        value: str,
        provider: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        self.value = value
        self.provider = provider
        self.created_at = created_at
        self.expires_at = expires_at

    @classmethod
    def generate(cls, provider: str, created_at: datetime) -> "OAuthState":
        return cls(
            # token_urlsafe over secrets, not uuid4 or random: this value is the
            # only thing standing between a forged callback and an accepted one.
            value=secrets.token_urlsafe(STATE_BYTES),
            provider=provider,
            created_at=created_at,
            expires_at=created_at + timedelta(minutes=STATE_TTL_MINUTES),
        )

    def is_expired_at(self, moment: datetime) -> bool:
        return moment >= self.expires_at

    def belongs_to(self, provider: str) -> bool:
        # A state minted for one provider must not validate a callback arriving on
        # another provider's route; otherwise the two handshakes are interchangeable.
        return self.provider == provider
