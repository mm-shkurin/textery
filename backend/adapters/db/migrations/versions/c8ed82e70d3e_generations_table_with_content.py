"""generations table with content

Revision ID: c8ed82e70d3e
Revises:
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c8ed82e70d3e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("volume_pages", sa.Integer(), nullable=False),
        sa.Column("requirements", sa.String(), nullable=True),
        sa.Column("extra_wishes", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed')",
            name="ck_generations_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("generations")
