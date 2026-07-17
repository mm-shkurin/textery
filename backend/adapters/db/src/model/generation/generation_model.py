import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from generation.generation import (
    COMPLETED_STATUS,
    FAILED_STATUS,
    IN_PROGRESS_STATUS,
    PENDING_STATUS,
    Generation,
)
from model.base import Base

ALLOWED_STATUSES = (PENDING_STATUS, IN_PROGRESS_STATUS, COMPLETED_STATUS, FAILED_STATUS)
_ALLOWED_STATUSES_SQL = ", ".join(repr(status) for status in ALLOWED_STATUSES)


class GenerationModel(Base):
    __tablename__ = "generations"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_ALLOWED_STATUSES_SQL})",
            name="ck_generations_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    volume_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    requirements: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extra_wishes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, generation: Generation) -> "GenerationModel":
        return cls(
            id=generation.id,
            owner_id=generation.owner_id,
            status=generation.status,
            created_at=generation.created_at,
            version=generation.version,
            topic=generation.topic,
            volume_pages=generation.volume_pages,
            requirements=generation.requirements,
            extra_wishes=generation.extra_wishes,
            document_type=generation.document_type,
            content=generation.content,
            error_message=generation.error_message,
        )

    def to_domain(self) -> Generation:
        return Generation(
            id=self.id,
            owner_id=self.owner_id,
            status=self.status,
            created_at=self.created_at,
            version=self.version,
            topic=self.topic,
            volume_pages=self.volume_pages,
            requirements=self.requirements,
            extra_wishes=self.extra_wishes,
            document_type=self.document_type,
            content=self.content,
            error_message=self.error_message,
        )
