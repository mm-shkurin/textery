import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from auth.account import Account
from model.base import Base


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, account: Account) -> "AccountModel":
        return cls(
            id=account.id,
            email=account.email,
            password_hash=account.password_hash,
            is_verified=account.is_verified,
            created_at=account.created_at,
        )

    def to_domain(self) -> Account:
        return Account(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            created_at=self.created_at,
        )
