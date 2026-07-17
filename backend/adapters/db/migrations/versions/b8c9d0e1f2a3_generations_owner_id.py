"""generations.owner_id

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows are deleted, not backfilled. They were created through the
    # anonymous endpoint this migration closes, so there is no account they could
    # honestly be attributed to; inventing one would fabricate ownership. Decided
    # 2026-07-17 -- the data is demo content. This runs on every environment.
    #
    # DELETE, not TRUNCATE: no other table references generations, so cascade
    # semantics buy nothing, and DELETE stays inside the migration's transaction --
    # a failure in the ALTER below rolls the rows back rather than leaving the
    # table emptied by a committed TRUNCATE.
    op.execute(sa.text("DELETE FROM generations"))
    # NOT NULL with no server_default: requesting a generation requires a token, so
    # an unowned generation is not a lesser mode -- it is a state that must not
    # exist. Same rule as documents.owner_id (a7b8c9d0e1f2). A server_default would
    # let a future insert that forgot the owner succeed silently against a sentinel
    # account instead of failing loudly.
    op.add_column(
        "generations",
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_generations_owner_id", "generations", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_generations_owner_id", table_name="generations")
    op.drop_column("generations", "owner_id")
