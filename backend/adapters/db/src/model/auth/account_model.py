import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
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
    name: Mapped[str | None] = mapped_column(Text, nullable=True)

    @classmethod
    def from_domain(cls, account: Account) -> "AccountModel":
        # Every column the entity carries is listed, and that completeness is the
        # point: this mapping used to omit failed_attempt_count, which was
        # invisible only because the column defaults to 0 and the sole caller is
        # registration, where 0 is right. `name` has no such alibi -- an INSERT
        # that skipped it would store NULL over a real value.
        #
        # There are three places that enumerate account columns by hand (here,
        # to_domain, and SqlAlchemyAccountRepository.save's update branch). A
        # field added to two of them produces a write that answers 200 and
        # persists nothing.
        return cls(
            id=account.id,
            email=account.email,
            password_hash=account.password_hash,
            is_verified=account.is_verified,
            created_at=account.created_at,
            failed_attempt_count=account.failed_attempt_count,
            name=account.name,
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
            name=self.name,
        )
