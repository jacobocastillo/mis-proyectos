"""
Achievement model module.

Responsibility:
- Define the catalog of possible achievements.
- Track which achievements a user has earned.
"""

from datetime import datetime, timezone

from app.extensions import db


class Achievement(db.Model):
    """Catalog entry for a defined achievement."""

    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    emoji = db.Column(db.String(10), nullable=False, default="🏆")
    xp_bonus = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "emoji": self.emoji,
            "xp_bonus": self.xp_bonus,
        }


class UserAchievement(db.Model):
    """Records a specific achievement earned by a user."""

    __tablename__ = "user_achievements"
    __table_args__ = (
        db.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    achievement_id = db.Column(
        db.Integer,
        db.ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
    )
    earned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship(
        "User",
        backref=db.backref("earned_achievements", lazy=True, cascade="all, delete-orphan"),
    )
    achievement = db.relationship(
        "Achievement",
        backref=db.backref("user_awards", lazy=True, cascade="all, delete-orphan"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "achievement": self.achievement.to_dict() if self.achievement else None,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
        }
