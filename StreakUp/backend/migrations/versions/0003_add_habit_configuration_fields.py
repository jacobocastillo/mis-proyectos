"""Add habit configuration fields.

Revision ID: 0003_add_habit_configuration_fields
Revises: 0002_add_pomodoro_sessions
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_habit_configuration_fields"
down_revision = "0002_add_pomodoro_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("habitos", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "tipo_validacion",
                sa.String(length=20),
                nullable=False,
                server_default="foto",
            )
        )
        batch_op.add_column(
            sa.Column(
                "frecuencia",
                sa.String(length=20),
                nullable=False,
                server_default="daily",
            )
        )
        batch_op.add_column(sa.Column("cantidad_objetivo", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("unidad_objetivo", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("duracion_objetivo_minutos", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_habitos_tipo_validacion",
            "tipo_validacion IN ('foto','texto','tiempo')",
        )
        batch_op.create_check_constraint(
            "ck_habitos_frecuencia",
            "frecuencia IN ('daily','weekly')",
        )
        batch_op.create_check_constraint(
            "ck_habitos_cantidad_objetivo_non_negative",
            "cantidad_objetivo IS NULL OR cantidad_objetivo >= 0",
        )
        batch_op.create_check_constraint(
            "ck_habitos_duracion_objetivo_non_negative",
            "duracion_objetivo_minutos IS NULL OR duracion_objetivo_minutos >= 0",
        )

    with op.batch_alter_table("habitos_usuario", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nombre_personalizado", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("descripcion_personalizada", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("tipo_validacion", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("frecuencia", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("cantidad_objetivo", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("unidad_objetivo", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("duracion_objetivo_minutos", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "fecha_actualizacion",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.create_check_constraint(
            "ck_habitos_usuario_tipo_validacion",
            "tipo_validacion IS NULL OR tipo_validacion IN ('foto','texto','tiempo')",
        )
        batch_op.create_check_constraint(
            "ck_habitos_usuario_frecuencia",
            "frecuencia IS NULL OR frecuencia IN ('daily','weekly')",
        )
        batch_op.create_check_constraint(
            "ck_habitos_usuario_cantidad_objetivo_non_negative",
            "cantidad_objetivo IS NULL OR cantidad_objetivo >= 0",
        )
        batch_op.create_check_constraint(
            "ck_habitos_usuario_duracion_objetivo_non_negative",
            "duracion_objetivo_minutos IS NULL OR duracion_objetivo_minutos >= 0",
        )

    with op.batch_alter_table("validaciones", schema=None) as batch_op:
        batch_op.drop_constraint("ck_validaciones_tipo_validacion", type_="check")
        batch_op.create_check_constraint(
            "ck_validaciones_tipo_validacion",
            "tipo_validacion IN ('foto','texto','tiempo','manual')",
        )


def downgrade() -> None:
    with op.batch_alter_table("validaciones", schema=None) as batch_op:
        batch_op.drop_constraint("ck_validaciones_tipo_validacion", type_="check")
        batch_op.create_check_constraint(
            "ck_validaciones_tipo_validacion",
            "tipo_validacion IN ('foto','tiempo','manual')",
        )

    with op.batch_alter_table("habitos_usuario", schema=None) as batch_op:
        batch_op.drop_constraint("ck_habitos_usuario_duracion_objetivo_non_negative", type_="check")
        batch_op.drop_constraint("ck_habitos_usuario_cantidad_objetivo_non_negative", type_="check")
        batch_op.drop_constraint("ck_habitos_usuario_frecuencia", type_="check")
        batch_op.drop_constraint("ck_habitos_usuario_tipo_validacion", type_="check")
        batch_op.drop_column("fecha_actualizacion")
        batch_op.drop_column("duracion_objetivo_minutos")
        batch_op.drop_column("unidad_objetivo")
        batch_op.drop_column("cantidad_objetivo")
        batch_op.drop_column("frecuencia")
        batch_op.drop_column("tipo_validacion")
        batch_op.drop_column("descripcion_personalizada")
        batch_op.drop_column("nombre_personalizado")

    with op.batch_alter_table("habitos", schema=None) as batch_op:
        batch_op.drop_constraint("ck_habitos_duracion_objetivo_non_negative", type_="check")
        batch_op.drop_constraint("ck_habitos_cantidad_objetivo_non_negative", type_="check")
        batch_op.drop_constraint("ck_habitos_frecuencia", type_="check")
        batch_op.drop_constraint("ck_habitos_tipo_validacion", type_="check")
        batch_op.drop_column("duracion_objetivo_minutos")
        batch_op.drop_column("unidad_objetivo")
        batch_op.drop_column("cantidad_objetivo")
        batch_op.drop_column("frecuencia")
        batch_op.drop_column("tipo_validacion")
