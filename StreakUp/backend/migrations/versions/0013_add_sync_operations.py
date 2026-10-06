"""Add sync operation receipts.

Revision ID: 0013_add_sync_operations
Revises: 0012_xp_logs_add_pomodoro_bonus_reason
Create Date: 2026-05-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_add_sync_operations"
down_revision = "0012_xp_logs_add_pomodoro_bonus_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_operation_id", sa.String(length=120), nullable=False),
        sa.Column("operation_type", sa.String(length=60), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('acked','failed','conflict')",
            name="ck_sync_operations_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "client_operation_id",
            name="uq_sync_operations_user_client_operation",
        ),
    )
    with op.batch_alter_table("sync_operations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sync_operations_user_id"),
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("sync_operations")
