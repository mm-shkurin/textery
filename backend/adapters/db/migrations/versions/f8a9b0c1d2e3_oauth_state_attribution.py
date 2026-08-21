"""park a marketing campaign against an OAuth handshake

Five nullable columns keyed on the CSRF state value. Without this table every
account created through a provider registers with NULL attribution -- a working
sign-up channel absent from every campaign report, biasing all of them toward the
email channel with nothing in the data to show it.

No foreign key to `oauth_states`, deliberately: that table is a security
mechanism whose rows are consumed and pruned on their own schedule, and an
analytics table must never be able to fail its cleanup.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d3
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UTM_COLUMNS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


def upgrade() -> None:
    op.create_table(
        "oauth_state_attribution",
        sa.Column("state_value", sa.String(), primary_key=True),
        *(sa.Column(column, sa.String(), nullable=True) for column in _UTM_COLUMNS),
    )


def downgrade() -> None:
    op.drop_table("oauth_state_attribution")
