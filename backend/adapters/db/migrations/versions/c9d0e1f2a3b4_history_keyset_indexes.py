"""composite indexes for owner-scoped history paging

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The column order mirrors the query exactly: equality on owner_id first, then the
# (created_at, id) pair the keyset seeks on, both DESC to match ORDER BY. Postgres
# can walk a backwards index scan, but only when the index's own direction matches
# -- an ASC index here would force a sort of the whole owner's history per page,
# which is precisely the cost the cursor exists to avoid.
_HISTORY_INDEX_COLUMNS = ("owner_id", sa.text("created_at DESC"), sa.text("id DESC"))


def upgrade() -> None:
    op.create_index("ix_generations_owner_history", "generations", list(_HISTORY_INDEX_COLUMNS))
    op.create_index("ix_documents_owner_history", "documents", list(_HISTORY_INDEX_COLUMNS))
    # The plain single-column owner indexes are now redundant: this composite leads
    # with owner_id, so it serves every lookup the old one did. Dropped rather than
    # left -- a redundant index costs a write on every insert and buys nothing.
    op.drop_index("ix_generations_owner_id", table_name="generations")
    op.drop_index("ix_documents_owner_id", table_name="documents")


def downgrade() -> None:
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_generations_owner_id", "generations", ["owner_id"])
    op.drop_index("ix_documents_owner_history", table_name="documents")
    op.drop_index("ix_generations_owner_history", table_name="generations")
