"""Add habit_id to shared_streak_groups and user_habit_id to shared_streak_memberships.

Revision ID: 0015_add_habit_binding_to_shared_streaks
Revises: 0014_add_token_blocklist
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_add_habit_binding_to_shared_streaks"
down_revision = "0014_add_token_blocklist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shared_streak_groups", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("habit_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "max_participants",
                sa.Integer(),
                nullable=False,
                server_default="3",
            )
        )
        batch_op.create_foreign_key(
            "fk_shared_streak_groups_habit_id",
            "habitos",
            ["habit_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("shared_streak_memberships", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("user_habit_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_shared_streak_memberships_user_habit_id",
            "habitos_usuario",
            ["user_habit_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("shared_streak_memberships", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_shared_streak_memberships_user_habit_id", type_="foreignkey"
        )
        batch_op.drop_column("user_habit_id")

    with op.batch_alter_table("shared_streak_groups", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_shared_streak_groups_habit_id", type_="foreignkey"
        )
        batch_op.drop_column("max_participants")
        batch_op.drop_column("habit_id")
