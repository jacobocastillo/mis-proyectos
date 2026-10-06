"""Extend xp_logs.fuente CHECK constraint to allow 'pomodoro_bonus'.

Revision ID: 0012_xp_logs_add_pomodoro_bonus_reason
Revises: 0011_pomodoro_interruption_bonus
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_xp_logs_add_pomodoro_bonus_reason"
down_revision = "0011_pomodoro_interruption_bonus"
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
            "fuente IN ('checkin','checkin_undo','validation','pomodoro','pomodoro_bonus')",
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "xp_logs",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_xp_logs_fuente",
            "fuente IN ('checkin','checkin_undo','validation','pomodoro')",
        )
