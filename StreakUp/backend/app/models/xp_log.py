"""
XP log model module.

Responsibility:
- Persist XP-related historical records.
"""

from datetime import datetime, timezone

from app.extensions import db


VALID_XP_REASONS = ("checkin", "checkin_undo", "validation", "pomodoro", "pomodoro_bonus")


class XpLog(db.Model):
    """Persist historical XP mutations for a user."""

    __tablename__ = "xp_logs"
    __table_args__ = (
        db.CheckConstraint(
            "fuente IN ('checkin','checkin_undo','validation','pomodoro','pomodoro_bonus')",
            name="ck_xp_logs_fuente",
        ),
        db.CheckConstraint(
            "source_event IN ('habit','achievement')",
            name="ck_xp_logs_source_event",
        ),
        db.Index("ix_xp_logs_habit_date", "usuario_id", "habit_id", "event_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        "usuario_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cantidad = db.Column(db.Integer, nullable=False)
    razon = db.Column("fuente", db.String(100), nullable=False)
    fecha = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    habit_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos_usuario.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_date = db.Column(db.Date, nullable=True)
    calculated_xp = db.Column(db.Integer, nullable=True)
    source_event = db.Column(
        db.String(20),
        nullable=False,
        default="habit",
        server_default="habit",
    )
    cap_hit = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    user = db.relationship("User", backref="xp_logs")
