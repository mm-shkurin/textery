"""add index on generations.status

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_generations_status", "generations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_generations_status", table_name="generations")
