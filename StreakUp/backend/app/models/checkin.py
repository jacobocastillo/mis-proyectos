"""
Check-in model module.

Responsibility:
- Store daily completion records for assigned user habits.
"""

from datetime import date as date_type

from app.extensions import db


class CheckIn(db.Model):
    """Daily check-in record for an assigned habit."""

    __tablename__ = "registro_habitos"
    __table_args__ = (
        db.UniqueConstraint("habitousuario_id", "fecha", name="uq_registro_habitos_fecha"),
        db.CheckConstraint("xp_ganado >= 0", name="ck_registro_habitos_xp_non_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    habitousuario_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos_usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha = db.Column(db.Date, nullable=False, default=lambda: date_type.today())
    completado = db.Column(db.Boolean, nullable=False, default=True)
    xp_ganado = db.Column(db.Integer, nullable=False, default=0)

    user_habit = db.relationship(
        "UserHabit",
        backref=db.backref("checkins", lazy=True, cascade="all, delete-orphan"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "habit_id": self.habitousuario_id,
            "date": self.fecha.isoformat() if self.fecha else None,
            "completed": self.completado,
            "xp_awarded": self.xp_ganado,
        }
