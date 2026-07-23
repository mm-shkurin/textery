import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from auth.oauth_identity import OAuthIdentity
from model.base import Base


class OAuthIdentityModel(Base):
    __tablename__ = "oauth_identities"
    # Uniqueness is on (provider, subject), never the email: the subject is the only
    # stable key a provider offers, and a DB constraint (not just application code) is
    # what guarantees one identity resolves to one account under a race.
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, identity: OAuthIdentity) -> "OAuthIdentityModel":
        return cls(
            id=identity.id,
            provider=identity.provider,
            subject=identity.subject,
            account_id=identity.account_id,
            created_at=identity.created_at,
        )

    def to_domain(self) -> OAuthIdentity:
        return OAuthIdentity.create(
            id=self.id,
            provider=self.provider,
            subject=self.subject,
            account_id=self.account_id,
            created_at=self.created_at,
        )
