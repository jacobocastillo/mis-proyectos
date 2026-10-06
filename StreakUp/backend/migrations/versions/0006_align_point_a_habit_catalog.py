"""Align Point A habit catalog metadata.

Revision ID: 0006_align_point_a_habit_catalog
Revises: c3db1f1fdb1f
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_align_point_a_habit_catalog"
down_revision = "c3db1f1fdb1f"
branch_labels = None
depends_on = None


TARGET_CATEGORIES = (
    {"id": 1, "nombre": "Salud y Bienestar", "descripcion": "Hábitos físicos y mentales"},
    {"id": 2, "nombre": "Productividad", "descripcion": "Enfoque y rendimiento"},
    {"id": 3, "nombre": "Aprendizaje", "descripcion": "Lectura, idiomas y estudio"},
)

TARGET_HABITS = (
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


def _catalog_tables() -> tuple[sa.Table, sa.Table]:
    metadata = sa.MetaData()
    categories = sa.Table(
        "categorias",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("nombre", sa.String),
        sa.Column("descripcion", sa.Text),
    )
    habits = sa.Table(
        "habitos",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("categoria_id", sa.Integer),
        sa.Column("nombre", sa.String),
        sa.Column("descripcion", sa.Text),
        sa.Column("dificultad", sa.String),
        sa.Column("xp_base", sa.Integer),
        sa.Column("meta_type", sa.String),
        sa.Column("xp_rate", sa.Integer),
        sa.Column("max_xp_per_day", sa.Integer),
        sa.Column("activo", sa.Boolean),
        sa.Column("tipo_validacion", sa.String),
        sa.Column("frecuencia", sa.String),
        sa.Column("cantidad_objetivo", sa.Integer),
        sa.Column("unidad_objetivo", sa.String),
        sa.Column("duracion_objetivo_minutos", sa.Integer),
    )
    return categories, habits


def _upsert_catalog_data() -> None:
    connection = op.get_bind()
    categories, habits = _catalog_tables()

    for row in TARGET_CATEGORIES:
        existing = connection.execute(
            sa.select(categories.c.id).where(categories.c.id == row["id"])
        ).scalar_one_or_none()
        if existing is None:
            connection.execute(categories.insert().values(**row))
        else:
            connection.execute(
                categories.update().where(categories.c.id == row["id"]).values(**row)
            )

    target_ids = [row["id"] for row in TARGET_HABITS]
    connection.execute(habits.update().values(activo=False))

    for row in TARGET_HABITS:
        values = {**row, "activo": True}
        existing = connection.execute(
            sa.select(habits.c.id).where(habits.c.id == row["id"])
        ).scalar_one_or_none()
        if existing is None:
            connection.execute(habits.insert().values(**values))
        else:
            connection.execute(
                habits.update().where(habits.c.id == row["id"]).values(**values)
            )

    connection.execute(
        habits.update().where(~habits.c.id.in_(target_ids)).values(activo=False)
    )


def upgrade() -> None:
    with op.batch_alter_table("habitos", schema=None) as batch_op:
        batch_op.drop_constraint("ck_habitos_tipo_validacion", type_="check")
        batch_op.add_column(
            sa.Column("meta_type", sa.String(length=40), nullable=False, server_default="boolean")
        )
        batch_op.add_column(sa.Column("xp_rate", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("max_xp_per_day", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_check_constraint(
            "ck_habitos_tipo_validacion",
            "tipo_validacion IN ('foto','texto','tiempo','photo','text_ai','time','check')",
        )
        batch_op.create_check_constraint(
            "ck_habitos_xp_rate_non_negative",
            "xp_rate >= 0",
        )
        batch_op.create_check_constraint(
            "ck_habitos_max_xp_per_day_non_negative",
            "max_xp_per_day >= 0",
        )

    with op.batch_alter_table("habitos_usuario", schema=None) as batch_op:
        batch_op.drop_constraint("ck_habitos_usuario_tipo_validacion", type_="check")
        batch_op.create_check_constraint(
            "ck_habitos_usuario_tipo_validacion",
            "tipo_validacion IS NULL OR tipo_validacion IN ('foto','texto','tiempo','photo','text_ai','time','check')",
        )

    _upsert_catalog_data()


def downgrade() -> None:
    habits = _catalog_tables()[1]
    connection = op.get_bind()
    connection.execute(
        habits.update()
        .where(habits.c.tipo_validacion == "photo")
        .values(tipo_validacion="foto")
    )
    connection.execute(
        habits.update()
        .where(habits.c.tipo_validacion == "text_ai")
        .values(tipo_validacion="texto")
    )
    connection.execute(
        habits.update()
        .where(habits.c.tipo_validacion == "time")
        .values(tipo_validacion="tiempo")
    )
    connection.execute(
        habits.update()
        .where(habits.c.tipo_validacion == "check")
        .values(tipo_validacion="texto")
    )

    with op.batch_alter_table("habitos_usuario", schema=None) as batch_op:
        batch_op.drop_constraint("ck_habitos_usuario_tipo_validacion", type_="check")
        batch_op.create_check_constraint(
            "ck_habitos_usuario_tipo_validacion",
            "tipo_validacion IS NULL OR tipo_validacion IN ('foto','texto','tiempo')",
        )

    with op.batch_alter_table("habitos", schema=None) as batch_op:
        batch_op.drop_constraint("ck_habitos_max_xp_per_day_non_negative", type_="check")
        batch_op.drop_constraint("ck_habitos_xp_rate_non_negative", type_="check")
        batch_op.drop_constraint("ck_habitos_tipo_validacion", type_="check")
        batch_op.create_check_constraint(
            "ck_habitos_tipo_validacion",
            "tipo_validacion IN ('foto','texto','tiempo')",
        )
        batch_op.drop_column("activo")
        batch_op.drop_column("max_xp_per_day")
        batch_op.drop_column("xp_rate")
        batch_op.drop_column("meta_type")
