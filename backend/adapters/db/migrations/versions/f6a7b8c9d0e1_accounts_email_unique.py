"""accounts email unique constraint

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_accounts_email", "accounts", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_accounts_email", "accounts", type_="unique")
