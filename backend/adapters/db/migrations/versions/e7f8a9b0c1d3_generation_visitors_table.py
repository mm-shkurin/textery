"""remember which browser requested each generation

One two-column table, owned entirely by analytics. Deliberately NOT a column on
`generations`: a generation's visitor is a marketing join key, nothing in the
product reads it, and the `Generation` entity's columns are enumerated by hand in
three places where a half-applied addition writes a row that answers 200 and
stores nothing.

No foreign key, on purpose. The two lifetimes are independent -- an account
erasure that deletes generations must not have to consider this table, and an
orphaned row here is one row nobody reads.

Revision ID: e7f8a9b0c1d3
Revises: d6e7f8a9b0c1
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d3"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_visitors",
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("visitor_id", postgresql.UUID(as_uuid=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generation_visitors")
