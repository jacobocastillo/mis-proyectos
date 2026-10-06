"""Initial schema baseline.

Revision ID: 0001_initial_baseline
Revises:
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False, unique=True),
        sa.Column("email", sa.String(length=120), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'user'")),
        sa.Column("total_xp", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("xp_in_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=False)
    op.create_index("idx_users_username", "users", ["username"], unique=False)

    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
    )
    op.create_index("idx_categorias_nombre", "categorias", ["nombre"], unique=False)

    op.create_table(
        "habitos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("dificultad", sa.String(length=20), nullable=False),
        sa.Column("xp_base", sa.Integer(), nullable=False),
        sa.CheckConstraint("dificultad IN ('facil','media','dificil')", name="ck_habitos_dificultad"),
        sa.CheckConstraint("xp_base >= 0", name="ck_habitos_xp_base_non_negative"),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_habitos_categoria", "habitos", ["categoria_id"], unique=False)

    op.create_table(
        "habitos_usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("habito_id", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["habito_id"], ["habitos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("usuario_id", "habito_id", "activo", name="uq_habitos_usuario_activo"),
    )
    op.create_index("idx_habitos_usuario_usuario", "habitos_usuario", ["usuario_id"], unique=False)
    op.create_index("idx_habitos_usuario_habito", "habitos_usuario", ["habito_id"], unique=False)

    op.create_table(
        "registro_habitos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("habitousuario_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("completado", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("xp_ganado", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint("xp_ganado >= 0", name="ck_registro_habitos_xp_non_negative"),
        sa.ForeignKeyConstraint(["habitousuario_id"], ["habitos_usuario.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("habitousuario_id", "fecha", name="uq_registro_habitos_fecha"),
    )
    op.create_index("idx_registro_fecha", "registro_habitos", ["fecha"], unique=False)

    op.create_table(
        "validaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("habitousuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo_validacion", sa.String(length=20), nullable=False),
        sa.Column("evidencia", sa.Text(), nullable=True),
        sa.Column("tiempo_segundos", sa.Integer(), nullable=True),
        sa.Column("validado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fecha", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("tipo_validacion IN ('foto','tiempo','manual')", name="ck_validaciones_tipo_validacion"),
        sa.ForeignKeyConstraint(["habitousuario_id"], ["habitos_usuario.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_validaciones_habitousuario", "validaciones", ["habitousuario_id"], unique=False)

    op.create_table(
        "xp_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("fuente", sa.String(length=100), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("fuente IN ('checkin','checkin_undo','validation')", name="ck_xp_logs_fuente"),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_xp_logs_usuario", "xp_logs", ["usuario_id"], unique=False)

    op.create_table(
        "niveles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("xp_minimo", sa.Integer(), nullable=False),
        sa.Column("xp_maximo", sa.Integer(), nullable=False),
        sa.Column("recompensa", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.CheckConstraint("xp_minimo < xp_maximo", name="ck_niveles_rango"),
    )


def downgrade() -> None:
    op.drop_table("niveles")
    op.drop_index("idx_xp_logs_usuario", table_name="xp_logs")
    op.drop_table("xp_logs")
    op.drop_index("idx_validaciones_habitousuario", table_name="validaciones")
    op.drop_table("validaciones")
    op.drop_index("idx_registro_fecha", table_name="registro_habitos")
    op.drop_table("registro_habitos")
    op.drop_index("idx_habitos_usuario_habito", table_name="habitos_usuario")
    op.drop_index("idx_habitos_usuario_usuario", table_name="habitos_usuario")
    op.drop_table("habitos_usuario")
    op.drop_index("idx_habitos_categoria", table_name="habitos")
    op.drop_table("habitos")
    op.drop_index("idx_categorias_nombre", table_name="categorias")
    op.drop_table("categorias")
    op.drop_index("idx_users_username", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
