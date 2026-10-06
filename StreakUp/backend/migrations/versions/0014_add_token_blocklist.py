"""Add token_blocklist table for JWT revocation.

Revision ID: 0014_add_token_blocklist
Revises: 0013_add_sync_operations
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_add_token_blocklist"
down_revision = "0013_add_sync_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_blocklist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("token_type", sa.String(length=10), nullable=False, server_default="access"),
        sa.Column("revoked_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_token_blocklist_jti"),
    )
    with op.batch_alter_table("token_blocklist", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_token_blocklist_jti"),
            ["jti"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("token_blocklist", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_token_blocklist_jti"))
    op.drop_table("token_blocklist")
