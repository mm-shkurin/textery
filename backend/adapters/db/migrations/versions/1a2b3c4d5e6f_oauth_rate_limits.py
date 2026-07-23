"""oauth rate-limit counters

Revision ID: 1a2b3c4d5e6f
Revises: 0f1a2b3c4d5e
Create Date: 2026-07-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "0f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite key (bucket, window): the abuse bound is a per-source, per-leg count
    # inside a fixed window, incremented with a single ON CONFLICT upsert so two
    # instances racing the same bucket still add up to one truthful count.
    op.create_table(
        "oauth_rate_limits",
        sa.Column("bucket_key", sa.String(), primary_key=True),
        sa.Column("window_start", sa.BigInteger(), primary_key=True),
        sa.Column("request_count", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("oauth_rate_limits")
