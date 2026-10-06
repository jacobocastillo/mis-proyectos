"""
Habit model module.

Responsibility:
- Define persistence structure for catalog habit entities.
"""

from decimal import Decimal

from app.extensions import db


def _json_number(value: object) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


class Category(db.Model):
    """Habit catalog category used only for foreign-key metadata."""

    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True, index=True)
    descripcion = db.Column(db.Text, nullable=True)


class Habit(db.Model):
    """Catalog habit entity loaded from the seeded schema."""

    __tablename__ = "habitos"
    __table_args__ = (
        db.CheckConstraint(
            "tipo_validacion IN ('foto','texto','tiempo','photo','text_ai','time','check')",
            name="ck_habitos_tipo_validacion",
        ),
        db.CheckConstraint(
            "frecuencia IN ('daily','weekly')",
            name="ck_habitos_frecuencia",
        ),
        db.CheckConstraint(
            "dificultad IN ('facil','media','dificil')",
            name="ck_habitos_dificultad",
        ),
        db.CheckConstraint("xp_base >= 0", name="ck_habitos_xp_base_non_negative"),
        db.CheckConstraint("xp_rate >= 0", name="ck_habitos_xp_rate_non_negative"),
        db.CheckConstraint(
            "max_xp_per_day >= 0",
            name="ck_habitos_max_xp_per_day_non_negative",
        ),
        db.CheckConstraint(
            "cantidad_objetivo IS NULL OR cantidad_objetivo >= 0",
            name="ck_habitos_cantidad_objetivo_non_negative",
        ),
        db.CheckConstraint(
            "duracion_objetivo_minutos IS NULL OR duracion_objetivo_minutos >= 0",
            name="ck_habitos_duracion_objetivo_non_negative",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("categorias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    dificultad = db.Column(db.String(20), nullable=False)
    xp_base = db.Column(db.Integer, nullable=False)
    meta_type = db.Column(
        db.String(40),
        nullable=False,
        default="boolean",
        server_default="boolean",
    )
    xp_rate = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    max_xp_per_day = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    tipo_validacion = db.Column(
        db.String(20),
        nullable=False,
        default="foto",
        server_default="foto",
    )
    frecuencia = db.Column(
        db.String(20),
        nullable=False,
        default="daily",
        server_default="daily",
    )
    cantidad_objetivo = db.Column(db.Numeric(8, 2), nullable=True)
    unidad_objetivo = db.Column(db.String(40), nullable=True)
    duracion_objetivo_minutos = db.Column(db.Integer, nullable=True)

    category = db.relationship("Category", backref=db.backref("habits", lazy=True))

    def to_dict(self) -> dict:
        """Return a JSON-safe representation for catalog consumers."""
        return {
            "id": self.id,
            "category_id": self.categoria_id,
            "name": self.nombre,
            "description": self.descripcion,
            "difficulty": self.dificultad,
            "xp_base": self.xp_base,
            "meta_type": self.meta_type,
            "xp_rate": self.xp_rate,
            "max_xp_per_day": self.max_xp_per_day,
            "active": bool(self.activo),
            "validation_type": self.tipo_validacion,
            "frequency": self.frecuencia,
            "target_quantity": _json_number(self.cantidad_objetivo),
            "target_unit": self.unidad_objetivo,
            "target_duration": self.duracion_objetivo_minutos,
        }
