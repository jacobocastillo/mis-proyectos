"""Merge the FCM token and shared streak migration branches.

Revision ID: 0017_merge_fcm_and_shared_streak_heads
Revises: 0014_add_user_fcm_token, 0016_add_duel_fields_to_shared_streaks
Create Date: 2026-10-06
"""

revision = "0017_merge_fcm_and_shared_streak_heads"
down_revision = (
    "0014_add_user_fcm_token",
    "0016_add_duel_fields_to_shared_streaks",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
