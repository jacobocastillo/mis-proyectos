"""
User-habit weekday schedule model module.

Responsibility:
- Persist which weekdays a user has chosen for a 'custom' frequency habit.
- weekday follows ISO convention: 0=Monday … 6=Sunday.
"""

from app.extensions import db


class UserHabitScheduleDay(db.Model):
    """Weekday slot for a custom-frequency user habit assignment."""

    __tablename__ = "habitos_usuario_schedule"
    __table_args__ = (
        db.UniqueConstraint(
            "habitousuario_id",
            "weekday",
            name="uq_habitos_usuario_schedule_day",
        ),
        db.CheckConstraint(
            "weekday BETWEEN 0 AND 6",
            name="ck_habitos_usuario_schedule_weekday",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    habitousuario_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos_usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weekday = db.Column(db.SmallInteger, nullable=False)

    def to_dict(self) -> dict:
        """Return a JSON-safe representation."""
        return {"id": self.id, "weekday": self.weekday}
