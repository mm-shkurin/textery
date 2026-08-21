"""add nullable text_style column to generations

Nullable with no server default and no CHECK: NULL means "the user chose no
register", which every row written before the style picker existed genuinely is,
and backfilling a default would claim a choice nobody made. The allowlist stays
in the domain — see `domain/src/generation/text_style.py`.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generations",
        sa.Column("text_style", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generations", "text_style")
