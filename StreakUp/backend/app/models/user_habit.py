"""
User-habit association model module.

Responsibility:
- Represent active catalog habit assignments for a user.
"""

from datetime import datetime, timezone

from sqlalchemy import true

from app.extensions import db


class UserHabit(db.Model):
    """User-to-catalog habit assignment."""

    __tablename__ = "habitos_usuario"
    __table_args__ = (
        db.UniqueConstraint("usuario_id", "habito_id", "activo", name="uq_habitos_usuario_activo"),
        db.CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="ck_habitos_usuario_fechas",
        ),
        db.CheckConstraint(
            "tipo_validacion IS NULL OR tipo_validacion IN ('foto','texto','tiempo','photo','text_ai','time','check')",
            name="ck_habitos_usuario_tipo_validacion",
        ),
        db.CheckConstraint(
            "frecuencia IS NULL OR frecuencia IN ('daily','weekly','custom')",
            name="ck_habitos_usuario_frecuencia",
        ),
        db.CheckConstraint(
            "cantidad_objetivo IS NULL OR cantidad_objetivo >= 0",
            name="ck_habitos_usuario_cantidad_objetivo_non_negative",
        ),
        db.CheckConstraint(
            "duracion_objetivo_minutos IS NULL OR duracion_objetivo_minutos >= 0",
            name="ck_habitos_usuario_duracion_objetivo_non_negative",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    habito_id = db.Column(
        db.Integer, db.ForeignKey("habitos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=true())
    nombre_personalizado = db.Column(db.String(120), nullable=True)
    descripcion_personalizada = db.Column(db.Text, nullable=True)
    tipo_validacion = db.Column(db.String(20), nullable=True)
    frecuencia = db.Column(db.String(20), nullable=True)
    cantidad_objetivo = db.Column(db.Numeric(8, 2), nullable=True)
    unidad_objetivo = db.Column(db.String(40), nullable=True)
    duracion_objetivo_minutos = db.Column(db.Integer, nullable=True)
    deadline_time = db.Column(db.String(5), nullable=True)
    min_text_length = db.Column(db.Integer, nullable=True)
    fecha_creacion = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )
    fecha_actualizacion = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=db.text("CURRENT_TIMESTAMP"),
    )

    user = db.relationship(
        "User",
        backref=db.backref("assigned_habits", lazy=True, cascade="all, delete-orphan"),
    )
    habit = db.relationship(
        "Habit",
        backref=db.backref("user_assignments", lazy=True, cascade="all, delete-orphan"),
    )
    schedule_days = db.relationship(
        "UserHabitScheduleDay",
        backref=db.backref("user_habit", lazy=True),
        cascade="all, delete-orphan",
        order_by="UserHabitScheduleDay.weekday",
        lazy="select",
    )
