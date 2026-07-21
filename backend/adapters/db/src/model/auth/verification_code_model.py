import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from auth.verification_code import VerificationCode
from model.base import Base


class VerificationCodeModel(Base):
    __tablename__ = "verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, code: VerificationCode, created_at: datetime) -> "VerificationCodeModel":
        return cls(
            id=code.id,
            account_id=code.account_id,
            code=code.code,
            expires_at=code.expires_at,
            consumed_at=code.consumed_at,
            created_at=created_at,
        )

    def to_domain(self) -> VerificationCode:
        return VerificationCode.reconstitute(
            id=self.id,
            account_id=self.account_id,
            code=self.code,
            expires_at=self.expires_at,
            created_at=self.created_at,
            consumed_at=self.consumed_at,
        )
