"""Add pomodoro sessions table.

Revision ID: 0002_add_pomodoro_sessions
Revises: 0001_initial_baseline
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_pomodoro_sessions"
down_revision = "0001_initial_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pomodoro_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("habit_id", sa.Integer(), nullable=True),
        sa.Column("theme", sa.String(length=20), nullable=False, server_default=sa.text("'fire'")),
        sa.Column("study_minutes", sa.Integer(), nullable=False, server_default=sa.text("25")),
        sa.Column("break_minutes", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("cycles", sa.Integer(), nullable=False, server_default=sa.text("4")),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("study_minutes > 0", name="ck_pomodoro_study_minutes_positive"),
        sa.CheckConstraint("break_minutes >= 0", name="ck_pomodoro_break_minutes_non_negative"),
        sa.CheckConstraint("cycles > 0", name="ck_pomodoro_cycles_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["habit_id"], ["habitos_usuario.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_pomodoro_sessions_user_started", "pomodoro_sessions", ["user_id", "started_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_pomodoro_sessions_user_started", table_name="pomodoro_sessions")
    op.drop_table("pomodoro_sessions")
