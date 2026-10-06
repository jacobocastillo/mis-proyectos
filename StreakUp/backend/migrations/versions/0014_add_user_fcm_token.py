"""Add fcm_token column to users table for push notification device registration.

Revision ID: 0014_add_user_fcm_token
Revises: 0013_add_sync_operations
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_add_user_fcm_token"
down_revision = "0013_add_sync_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("fcm_token", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "fcm_token")
