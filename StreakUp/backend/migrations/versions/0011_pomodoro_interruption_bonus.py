"""Add interruption_count and bonus_xp_awarded to pomodoro_sessions.

Revision ID: 0011_pomodoro_interruption_bonus
Revises: 0010_xp_logs_add_pomodoro_reason
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_pomodoro_interruption_bonus"
down_revision = "0010_xp_logs_add_pomodoro_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pomodoro_sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "interruption_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("bonus_xp_awarded", sa.Integer(), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_pomodoro_interruption_count_non_negative",
            "interruption_count >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("pomodoro_sessions", schema=None, recreate="always") as batch_op:
        batch_op.drop_column("bonus_xp_awarded")
        batch_op.drop_column("interruption_count")
