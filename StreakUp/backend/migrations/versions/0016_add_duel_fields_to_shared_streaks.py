"""Add duel fields to shared streak groups and memberships.

Revision ID: 0016_add_duel_fields_to_shared_streaks
Revises: 0015_add_habit_binding_to_shared_streaks
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_add_duel_fields_to_shared_streaks"
down_revision = "0015_add_habit_binding_to_shared_streaks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shared_streak_groups", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "start_date",
                sa.Date(),
                nullable=False,
                server_default=sa.text("CURRENT_DATE"),
            )
        )
        batch_op.add_column(sa.Column("duration_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("end_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "group_status",
                sa.String(20),
                nullable=False,
                server_default="active",
            )
        )
        batch_op.add_column(sa.Column("winner_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_shared_streak_groups_winner_user_id",
            "users",
            ["winner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint(
            "ck_shared_streak_groups_group_status",
            "group_status IN ('active','finished')",
        )

    with op.batch_alter_table("shared_streak_memberships", schema=None) as batch_op:
        batch_op.drop_constraint("ck_shared_streak_memberships_status", type_="check")
        batch_op.add_column(sa.Column("lost_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "completed_days",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_check_constraint(
            "ck_shared_streak_memberships_status",
            "status IN ('active','left','lost','winner')",
        )


def downgrade() -> None:
    with op.batch_alter_table("shared_streak_memberships", schema=None) as batch_op:
        batch_op.drop_constraint("ck_shared_streak_memberships_status", type_="check")
        batch_op.drop_column("completed_days")
        batch_op.drop_column("lost_at")
        batch_op.create_check_constraint(
            "ck_shared_streak_memberships_status",
            "status IN ('active','left')",
        )

    with op.batch_alter_table("shared_streak_groups", schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_shared_streak_groups_group_status", type_="check"
        )
        batch_op.drop_constraint(
            "fk_shared_streak_groups_winner_user_id", type_="foreignkey"
        )
        batch_op.drop_column("winner_user_id")
        batch_op.drop_column("group_status")
        batch_op.drop_column("end_date")
        batch_op.drop_column("duration_days")
        batch_op.drop_column("start_date")
