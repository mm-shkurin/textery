import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from generation.generation import Generation
from model.base import Base

ALLOWED_STATUSES = ("pending", "in_progress", "completed", "failed")


class GenerationModel(Base):
    __tablename__ = "generations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed')",
            name="ck_generations_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    volume_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    requirements: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extra_wishes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    document_type: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, generation: Generation) -> "GenerationModel":
        return cls(
            id=generation.id,
            status=generation.status,
            created_at=generation.created_at,
            topic=generation.topic,
            volume_pages=generation.volume_pages,
            requirements=generation.requirements,
            extra_wishes=generation.extra_wishes,
            document_type=generation.document_type,
        )

    def to_domain(self) -> Generation:
        return Generation(
            id=self.id,
            status=self.status,
            created_at=self.created_at,
            topic=self.topic,
            volume_pages=self.volume_pages,
            requirements=self.requirements,
            extra_wishes=self.extra_wishes,
            document_type=self.document_type,
        )
