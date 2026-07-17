"""documents table

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALLOWED_DOCUMENT_TYPES_SQL = "'доклад', 'эссе', 'сочинение', 'реферат'"


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # NOT NULL: creating a document requires a token, so an unowned document is
        # not a lesser mode -- it is a state that must not exist. See
        # decisions/document-ownership-decision.md.
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        # Text, not VARCHAR(200000), deliberately. The 200,000-character cap is an
        # INPUT contract measured before sanitization; sanitizing escapes as well as
        # strips (& -> &amp;), so a legitimate 200k input can persist far longer. A
        # length constraint here would reject valid saves with a raw constraint
        # message -- exactly what Security 5.1 forbids leaking.
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"document_type IN ({_ALLOWED_DOCUMENT_TYPES_SQL})",
            name="ck_documents_document_type",
        ),
        sa.CheckConstraint("status IN ('draft')", name="ck_documents_status"),
        sa.CheckConstraint("version >= 1", name="ck_documents_version_positive"),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    # The idempotency guard is the constraint itself, not a check-then-insert:
    # mirrors uq_accounts_email (story 7 scenario 2.2), whose whole point was to
    # make the concurrent case (2.4a) safe without a TOCTOU window. Scoped to the
    # owner -- a global key namespace would let one account's key return another
    # account's document.
    op.create_unique_constraint(
        "uq_documents_owner_idempotency_key",
        "documents",
        ["owner_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_documents_owner_idempotency_key", "documents", type_="unique")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")
