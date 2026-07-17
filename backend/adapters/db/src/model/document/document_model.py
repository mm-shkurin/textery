import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from document.document import ALLOWED_STATUSES, Document
from document.document_type import SUPPORTED_DOCUMENT_TYPES
from model.base import Base

_ALLOWED_STATUSES_SQL = ", ".join(repr(status) for status in ALLOWED_STATUSES)
_ALLOWED_DOCUMENT_TYPES_SQL = ", ".join(repr(value) for value in SUPPORTED_DOCUMENT_TYPES)


class DocumentModel(Base):
    __tablename__ = "documents"
    __table_args__ = (
        # The allowlists live in the domain; the DB only constrains. Built from the
        # domain constants so the two cannot drift -- same approach as
        # GenerationModel's ck_generations_status.
        CheckConstraint(
            f"document_type IN ({_ALLOWED_DOCUMENT_TYPES_SQL})",
            name="ck_documents_document_type",
        ),
        CheckConstraint(f"status IN ({_ALLOWED_STATUSES_SQL})", name="ck_documents_status"),
        CheckConstraint("version >= 1", name="ck_documents_version_positive"),
        UniqueConstraint("owner_id", "idempotency_key", name="uq_documents_owner_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentModel":
        return cls(
            id=document.id,
            owner_id=document.owner_id,
            document_type=document.document_type,
            status=document.status,
            content=document.content,
            version=document.version,
            idempotency_key=document.idempotency_key,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    def to_domain(self) -> Document:
        # reconstitute, not create(): create() hardcodes draft/empty/version=1, so
        # reading a saved document through it would blank the content and reset the
        # CAS token to 1 on every read. Story 7 shipped exactly this bug via
        # AccountModel.to_domain and every account read back unverified.
        return Document.reconstitute(
            id=self.id,
            owner_id=self.owner_id,
            document_type=self.document_type,
            status=self.status,
            content=self.content,
            version=self.version,
            idempotency_key=self.idempotency_key,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
