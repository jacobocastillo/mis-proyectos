"""
Catalog bootstrap service module.

Responsibility:
- Define the canonical hosted catalog data.
- Seed that catalog idempotently without demo users.
"""

from app.extensions import db
from app.models.habit import Category, Habit


DEFAULT_CATEGORIES = (
    {"id": 1, "nombre": "Salud y Bienestar", "descripcion": "Hábitos físicos y mentales"},
    {"id": 2, "nombre": "Productividad", "descripcion": "Enfoque y rendimiento"},
    {"id": 3, "nombre": "Aprendizaje", "descripcion": "Lectura, idiomas y estudio"},
)

DEFAULT_HABITS = (
    {
        "id": 1,
        "categoria_id": 1,
        "nombre": "Beber agua",
        "descripcion": "Mantener hidratación diaria",
        "dificultad": "facil",
        "xp_base": 20,
        "meta_type": "quantity_liters",
        "xp_rate": 0,
        "max_xp_per_day": 20,
        "tipo_validacion": "photo",
        "frecuencia": "daily",
        "cantidad_objetivo": 2,
        "unidad_objetivo": "litros",
        "duracion_objetivo_minutos": None,
    },
    {
        "id": 2,
        "categoria_id": 1,
        "nombre": "Ejercicio",
        "descripcion": "Actividad física diaria",
        "dificultad": "media",
        "xp_base": 0,
        "meta_type": "minutes",
        "xp_rate": 1,
        "max_xp_per_day": 60,
        "tipo_validacion": "time",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": 30,
    },
    {
        "id": 3,
        "categoria_id": 1,
        "nombre": "Comida saludable",
        "descripcion": "Alimentación balanceada",
        "dificultad": "media",
        "xp_base": 25,
        "meta_type": "boolean",
        "xp_rate": 0,
        "max_xp_per_day": 25,
        "tipo_validacion": "photo",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": None,
    },
    {
        "id": 4,
        "categoria_id": 1,
        "nombre": "Meditar",
        "descripcion": "Relajación mental",
        "dificultad": "facil",
        "xp_base": 10,
        "meta_type": "minutes",
        "xp_rate": 1,
        "max_xp_per_day": 25,
        "tipo_validacion": "time",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": 10,
    },
    {
        "id": 7,
        "categoria_id": 2,
        "nombre": "Tarea clave",
        "descripcion": "Tarea importante del día",
        "dificultad": "media",
        "xp_base": 30,
        "meta_type": "boolean",
        "xp_rate": 0,
        "max_xp_per_day": 30,
        "tipo_validacion": "text_ai",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": None,
    },
    {
        "id": 8,
        "categoria_id": 2,
        "nombre": "Empezar antes de X hora",
        "descripcion": "Disciplina matutina",
        "dificultad": "media",
        "xp_base": 20,
        "meta_type": "boolean",
        "xp_rate": 0,
        "max_xp_per_day": 20,
        "tipo_validacion": "check",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": None,
    },
    {
        "id": 9,
        "categoria_id": 3,
        "nombre": "Leer",
        "descripcion": "Lectura diaria",
        "dificultad": "facil",
        "xp_base": 0,
        "meta_type": "minutes",
        "xp_rate": 1,
        "max_xp_per_day": 30,
        "tipo_validacion": "time",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": "minutos",
        "duracion_objetivo_minutos": 20,
    },
    {
        "id": 10,
        "categoria_id": 3,
        "nombre": "Practicar idioma",
        "descripcion": "Aprendizaje lingüístico",
        "dificultad": "media",
        "xp_base": 25,
        "meta_type": "boolean",
        "xp_rate": 0,
        "max_xp_per_day": 25,
        "tipo_validacion": "text_ai",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": None,
    },
    {
        "id": 6,
        "categoria_id": 2,
        "nombre": "Trabajo profundo",
        "descripcion": "Sesión sin distracciones",
        "dificultad": "dificil",
        "xp_base": 0,
        "meta_type": "minutes",
        "xp_rate": 1,
        "max_xp_per_day": 60,
        "tipo_validacion": "time",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": 60,
    },
    {
        "id": 13,
        "categoria_id": 3,
        "nombre": "Escribir diario",
        "descripcion": "Reflexión escrita diaria",
        "dificultad": "facil",
        "xp_base": 20,
        "meta_type": "boolean",
        "xp_rate": 0,
        "max_xp_per_day": 20,
        "tipo_validacion": "text_ai",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": None,
    },
    {
        "id": 14,
        "categoria_id": 3,
        "nombre": "Estudiar",
        "descripcion": "Sesión de estudio enfocada",
        "dificultad": "media",
        "xp_base": 0,
        "meta_type": "minutes",
        "xp_rate": 1,
        "max_xp_per_day": 45,
        "tipo_validacion": "time",
        "frecuencia": "daily",
        "cantidad_objetivo": None,
        "unidad_objetivo": None,
        "duracion_objetivo_minutos": 45,
    },
)

DEFAULT_HABIT_IDS = (1, 3, 2, 4, 7, 8, 9, 10, 6, 13, 14)


def seed_catalog() -> dict[str, int]:
    """Insert the canonical catalog rows without creating demo users."""
    categories_created = 0
    habits_created = 0

    for row in DEFAULT_CATEGORIES:
        category = db.session.get(Category, row["id"])
        if category is None:
            category = Category(id=row["id"])
            db.session.add(category)
            categories_created += 1

        category.nombre = row["nombre"]
        category.descripcion = row["descripcion"]

    Habit.query.filter(~Habit.id.in_(DEFAULT_HABIT_IDS)).update(
        {Habit.activo: False},
        synchronize_session=False,
    )

    for row in DEFAULT_HABITS:
        habit = db.session.get(Habit, row["id"])
        if habit is None:
            habit = Habit(id=row["id"])
            db.session.add(habit)
            habits_created += 1

        habit.categoria_id = row["categoria_id"]
        habit.nombre = row["nombre"]
        habit.descripcion = row["descripcion"]
        habit.dificultad = row["dificultad"]
        habit.xp_base = row["xp_base"]
        habit.meta_type = row["meta_type"]
        habit.xp_rate = row["xp_rate"]
        habit.max_xp_per_day = row["max_xp_per_day"]
        habit.activo = True
        habit.tipo_validacion = row["tipo_validacion"]
        habit.frecuencia = row["frecuencia"]
        habit.cantidad_objetivo = row["cantidad_objetivo"]
        habit.unidad_objetivo = row["unidad_objetivo"]
        habit.duracion_objetivo_minutos = row["duracion_objetivo_minutos"]

    db.session.commit()

    return {
        "categories_created": categories_created,
        "habits_created": habits_created,
        "total_categories": Category.query.count(),
        "total_habits": Habit.query.count(),
    }
