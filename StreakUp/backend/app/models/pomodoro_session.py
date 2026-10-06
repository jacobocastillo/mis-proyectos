"""
Pomodoro session model module.

Responsibility:
- Store pomodoro timer sessions for users.
"""

from datetime import datetime, timezone

from app.extensions import db


POMODORO_BONUS_XP = 10


class PomodoroSession(db.Model):
    """A Pomodoro timer session."""

    __tablename__ = "pomodoro_sessions"
    __table_args__ = (
        db.CheckConstraint("study_minutes > 0", name="ck_pomodoro_study_minutes_positive"),
        db.CheckConstraint("break_minutes >= 0", name="ck_pomodoro_break_minutes_non_negative"),
        db.CheckConstraint("cycles > 0", name="ck_pomodoro_cycles_positive"),
        db.CheckConstraint("interruption_count >= 0", name="ck_pomodoro_interruption_count_non_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    habit_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos_usuario.id", ondelete="SET NULL"),
        nullable=True,
    )
    theme = db.Column(db.String(20), nullable=False, default="fire")
    study_minutes = db.Column(db.Integer, nullable=False, default=25)
    break_minutes = db.Column(db.Integer, nullable=False, default=5)
    cycles = db.Column(db.Integer, nullable=False, default=4)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    interruption_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    bonus_xp_awarded = db.Column(db.Integer, nullable=True)
    started_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("pomodoro_sessions", lazy=True))
    habit = db.relationship("UserHabit", backref=db.backref("pomodoro_sessions", lazy=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "habit_id": self.habit_id,
            "theme": self.theme,
            "study_minutes": self.study_minutes,
            "break_minutes": self.break_minutes,
            "cycles": self.cycles,
            "completed": self.completed,
            "interruption_count": self.interruption_count,
            "bonus_xp_awarded": self.bonus_xp_awarded,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
