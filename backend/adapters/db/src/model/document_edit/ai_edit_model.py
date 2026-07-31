import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from model.base import Base


class AiEditModel(Base):
    """An AI edit of a document.

    Deliberately two columns. `status`, `created_at` and `last_seq` belong to
    scenario 3.1 and are added additively the day a Statements line first reads
    them -- a column no test reads is a column no test constrains.

    `document_id` is a real foreign key, not a bare UUID: the suite empties itself
    with one `TRUNCATE ... CASCADE`, and CASCADE only reaches tables connected by a
    foreign key (see tests/statements/database_cleanup.py, whose docstring records
    the last time that list drifted and cleanup silently stopped happening). Without
    the FK, edits would accumulate across the suite and an edit could outlive its
    document -- so the guard would resolve the scope of an edit whose document is
    gone.
    """

    __tablename__ = "ai_edits"

    # The index lives here as well as in the migration, because `Base.metadata` is
    # what autogenerate compares the live database against: an index present only in
    # the migration reads as one the model never asked for, and the next
    # `--autogenerate` proposes dropping it. Every sibling model declares its indexes
    # the same way for the same reason.
    __table_args__ = (Index("ix_ai_edits_document_id", "document_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
