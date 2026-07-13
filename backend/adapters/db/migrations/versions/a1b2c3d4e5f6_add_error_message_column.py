"""add error_message column to generations

Revision ID: a1b2c3d4e5f6
Revises: c8ed82e70d3e
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c8ed82e70d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("error_message", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("generations", "error_message")
