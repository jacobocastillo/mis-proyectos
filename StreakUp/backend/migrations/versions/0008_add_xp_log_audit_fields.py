"""Add XP log audit fields for habit, event date, cap, and source.

Revision ID: 0008_add_xp_log_audit_fields
Revises: 0007_add_point_a_user_habit_config
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_add_xp_log_audit_fields"
down_revision = "0007_add_point_a_user_habit_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("xp_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("habit_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("event_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("calculated_xp", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source_event",
                sa.String(length=20),
                nullable=False,
                server_default="habit",
            )
        )
        batch_op.add_column(
            sa.Column(
                "cap_hit",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_foreign_key(
            "fk_xp_logs_habit_id",
            "habitos_usuario",
            ["habit_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_xp_logs_habit_date",
            ["usuario_id", "habit_id", "event_date"],
        )


def downgrade() -> None:
    with op.batch_alter_table("xp_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_xp_logs_habit_date")
        batch_op.drop_constraint("fk_xp_logs_habit_id", type_="foreignkey")
        batch_op.drop_column("cap_hit")
        batch_op.drop_column("source_event")
        batch_op.drop_column("calculated_xp")
        batch_op.drop_column("event_date")
        batch_op.drop_column("habit_id")
