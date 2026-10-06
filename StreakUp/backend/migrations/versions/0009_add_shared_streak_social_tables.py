"""Add invite-only shared streak social tables.

Revision ID: 0009_add_shared_streak_social_tables
Revises: 0008_add_xp_log_audit_fields
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_add_shared_streak_social_tables"
down_revision = "0008_add_xp_log_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shared_streak_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("invite_code", sa.String(length=24), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("length(name) >= 3", name="ck_shared_streak_groups_name_length"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code", name="uq_shared_streak_groups_invite_code"),
    )
    op.create_index(
        op.f("ix_shared_streak_groups_owner_user_id"),
        "shared_streak_groups",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shared_streak_groups_invite_code"),
        "shared_streak_groups",
        ["invite_code"],
        unique=False,
    )

    op.create_table(
        "shared_streak_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("share_progress", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("left_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('active','left')",
            name="ck_shared_streak_memberships_status",
        ),
        sa.ForeignKeyConstraint(["group_id"], ["shared_streak_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_shared_streak_membership_user"),
    )
    op.create_index(
        op.f("ix_shared_streak_memberships_group_id"),
        "shared_streak_memberships",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_shared_streak_memberships_user_id"),
        "shared_streak_memberships",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shared_streak_memberships_user_id"), table_name="shared_streak_memberships")
    op.drop_index(op.f("ix_shared_streak_memberships_group_id"), table_name="shared_streak_memberships")
    op.drop_table("shared_streak_memberships")
    op.drop_index(op.f("ix_shared_streak_groups_invite_code"), table_name="shared_streak_groups")
    op.drop_index(op.f("ix_shared_streak_groups_owner_user_id"), table_name="shared_streak_groups")
    op.drop_table("shared_streak_groups")
