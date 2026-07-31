"""ai_edits table

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Two columns, deliberately. Scenario 3.1 adds status/created_at/last_seq
    # additively when a statement first reads them.
    op.create_table(
        "ai_edits",
        # PRIMARY KEY, not a plain column: a retried insert would otherwise leave
        # two rows with the same id and turn the scope finder's one_or_none() into
        # MultipleResultsFound on the guard path.
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # A real foreign key, not a bare UUID. The test suite empties itself with a
        # single TRUNCATE ... CASCADE, and CASCADE only reaches tables connected by
        # a foreign key -- without it, edits accumulate across the suite and an edit
        # outlives a deleted document, so the guard resolves the scope of an edit
        # whose document is gone.
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    # The scope finder filters on both ids; the index leads with document_id so it
    # also covers the by-document listing scenario 3.1 will need.
    op.create_index("ix_ai_edits_document_id", "ai_edits", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_edits_document_id", table_name="ai_edits")
    op.drop_table("ai_edits")
