"""link a document to the generation it was converted from

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-31

The UNIQUE constraint is the feature, not bookkeeping. It is what makes the
conversion idempotent AND race-safe across instances: a replayed request and two
concurrent requests both lose the insert atomically, and the usecase answers by
returning the document that won. Without it, "check whether this generation was
already converted, then insert" is a TOCTOU window that a double-mounted editor
(React StrictMode double-invokes effects) walks straight into, and the user ends
up with two documents holding the same text.

Nullable because a manual document has no generation, and NULLs do not collide
under a UNIQUE constraint in Postgres -- every manual document keeps its own row
without ever contending for this key.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_documents_generation_id",
        "documents",
        ["generation_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_documents_generation_id", "documents", type_="unique")
    op.drop_column("documents", "generation_id")
