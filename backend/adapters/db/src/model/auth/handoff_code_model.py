import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from auth.handoff_code import HandoffCode
from model.base import Base


class HandoffCodeModel(Base):
    __tablename__ = "oauth_handoff_codes"

    # The opaque code is the primary key and the only lookup key. Redemption is a
    # conditional delete of this row, which is what makes the code single-use and lets
    # exactly one of two concurrent exchanges win the row lock.
    value: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, code: HandoffCode) -> "HandoffCodeModel":
        return cls(
            value=code.value,
            account_id=code.account_id,
            created_at=code.created_at,
            expires_at=code.expires_at,
        )
