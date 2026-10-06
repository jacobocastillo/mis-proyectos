"""
Social sharing models.

Responsibility:
- Store invite-only shared streak groups and explicit sharing memberships.
"""

from datetime import date as date_type, datetime, timezone

from app.extensions import db


class SharedStreakGroup(db.Model):
    """Invite-only group used for shared streak tracking."""

    __tablename__ = "shared_streak_groups"
    __table_args__ = (
        db.UniqueConstraint("invite_code", name="uq_shared_streak_groups_invite_code"),
        db.CheckConstraint("length(name) >= 3", name="ck_shared_streak_groups_name_length"),
        db.CheckConstraint(
            "group_status IN ('active','finished')",
            name="ck_shared_streak_groups_group_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    habit_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winner_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = db.Column(db.String(120), nullable=False)
    invite_code = db.Column(db.String(24), nullable=False, index=True)
    max_participants = db.Column(
        db.Integer, nullable=False, default=3, server_default="3"
    )
    start_date = db.Column(
        db.Date,
        nullable=False,
        default=lambda: date_type.today(),
        server_default=db.text("CURRENT_DATE"),
    )
    duration_days = db.Column(db.Integer, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    group_status = db.Column(
        db.String(20), nullable=False, default="active", server_default="active"
    )
    active = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    owner = db.relationship(
        "User",
        foreign_keys=[owner_user_id],
        backref=db.backref("owned_shared_streak_groups", lazy=True, cascade="all, delete-orphan"),
    )
    winner = db.relationship(
        "User",
        foreign_keys=[winner_user_id],
        backref=db.backref("won_shared_streak_groups", lazy=True),
    )
    habit = db.relationship("Habit", backref=db.backref("shared_streak_groups", lazy=True))


class SharedStreakMembership(db.Model):
    """Explicit user membership and progress-sharing consent for one group."""

    __tablename__ = "shared_streak_memberships"
    __table_args__ = (
        db.UniqueConstraint("group_id", "user_id", name="uq_shared_streak_membership_user"),
        db.CheckConstraint(
            "status IN ('active','left','lost','winner')",
            name="ck_shared_streak_memberships_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("shared_streak_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_habit_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos_usuario.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, default="active", server_default="active")
    share_progress = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    completed_days = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    joined_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    left_at = db.Column(db.DateTime, nullable=True)
    lost_at = db.Column(db.DateTime, nullable=True)

    group = db.relationship(
        "SharedStreakGroup",
        backref=db.backref("memberships", lazy=True, cascade="all, delete-orphan"),
    )
    user = db.relationship(
        "User",
        backref=db.backref("shared_streak_memberships", lazy=True, cascade="all, delete-orphan"),
    )
    user_habit = db.relationship(
        "UserHabit", backref=db.backref("shared_streak_memberships", lazy=True)
    )
