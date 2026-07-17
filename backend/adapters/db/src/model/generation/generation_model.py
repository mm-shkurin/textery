import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
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
        # Serves the owner-scoped history keyset: equality on owner_id, then the
        # (created_at, id) pair the cursor seeks on, DESC to match ORDER BY. Leads
        # with owner_id, so it also covers every plain by-owner lookup -- which is
        # why there is no separate index=True on the column.
        Index(
            "ix_generations_owner_history",
            "owner_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        # The stale sweep's exact predicate. Leads with status so the scan never
        # touches completed/failed rows, which are most of the table and are
        # never sweepable.
        Index("ix_generations_sweep", "status", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    # index=False: ix_generations_sweep above leads with status and serves
    # every query that a status-only index would.
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Storage-owned, like DocumentModel.updated_at: the domain has no such
    # field and does not need one. It exists so the sweep can ask "has this
    # row made progress recently", which created_at cannot answer -- it never
    # changes, so a requeued row stayed stale forever and was re-triggered on
    # every sweep.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    volume_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    requirements: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_wishes: Mapped[str | None] = mapped_column(String, nullable=True)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, generation: Generation) -> "GenerationModel":
        return cls(
            id=generation.id,
            owner_id=generation.owner_id,
            status=generation.status,
            created_at=generation.created_at,
            # A brand-new row's last progress is its creation. Subsequent
            # transitions bump it in SQL (see SqlAlchemyGenerationStorage.update).
            updated_at=generation.created_at,
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
