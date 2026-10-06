"""Extend xp_logs.fuente CHECK constraint to allow 'pomodoro'.

Revision ID: 0010_xp_logs_add_pomodoro_reason
Revises: 0009_add_shared_streak_social_tables
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_xp_logs_add_pomodoro_reason"
down_revision = "0009_add_shared_streak_social_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table(
        "xp_logs",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_xp_logs_fuente",
            "fuente IN ('checkin','checkin_undo','validation','pomodoro')",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "xp_logs",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_xp_logs_fuente",
            "fuente IN ('checkin','checkin_undo','validation')",
        )
