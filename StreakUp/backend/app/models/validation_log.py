"""
Validation log model module.

Responsibility:
- Store image-validation attempts for assigned user habits.
"""

from datetime import datetime, timezone

from app.extensions import db


class ValidationLog(db.Model):
    """Stores the result of an AI-powered habit validation."""

    __tablename__ = "validaciones"
    __table_args__ = (
        db.CheckConstraint(
            "tipo_validacion IN ('foto','texto','tiempo','manual')",
            name="ck_validaciones_tipo_validacion",
        ),
        db.CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_validaciones_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    habitousuario_id = db.Column(
        db.Integer,
        db.ForeignKey("habitos_usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_validacion = db.Column(db.String(20), nullable=False, default="foto")
    evidencia = db.Column(db.Text, nullable=True)
    tiempo_segundos = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    validado = db.Column(db.Boolean, nullable=False, default=False)
    fecha = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    user_habit = db.relationship(
        "UserHabit",
        backref=db.backref("validations", lazy=True, cascade="all, delete-orphan"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "habit_id": self.habitousuario_id,
            "status": self.status,
            "valid": self.validado,
            "created_at": self.fecha.isoformat() if self.fecha else None,
        }
