import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
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
    failed_attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )

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
        # reconstitute, not the constructor: the constructor hardcodes
        # is_verified=False (correct for *creating* an account, wrong for reading
        # one back), which would make every stored account read as unverified --
        # no verified user could ever log in.
        return Account.reconstitute(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            created_at=self.created_at,
            is_verified=self.is_verified,
            failed_attempt_count=self.failed_attempt_count,
        )
