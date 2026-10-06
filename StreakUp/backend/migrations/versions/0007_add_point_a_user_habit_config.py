"""Add Point A user habit configuration fields.

Revision ID: 0007_add_point_a_user_habit_config
Revises: 0006_align_point_a_habit_catalog
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_add_point_a_user_habit_config"
down_revision = "0006_align_point_a_habit_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("habitos", schema=None) as batch_op:
        batch_op.alter_column(
            "cantidad_objetivo",
            existing_type=sa.Integer(),
            type_=sa.Numeric(8, 2),
            existing_nullable=True,
        )

    with op.batch_alter_table("habitos_usuario", schema=None) as batch_op:
        batch_op.alter_column(
            "cantidad_objetivo",
            existing_type=sa.Integer(),
            type_=sa.Numeric(8, 2),
            existing_nullable=True,
        )
        batch_op.add_column(sa.Column("deadline_time", sa.String(length=5), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("habitos_usuario", schema=None) as batch_op:
        batch_op.drop_column("deadline_time")
        batch_op.alter_column(
            "cantidad_objetivo",
            existing_type=sa.Numeric(8, 2),
            type_=sa.Integer(),
            existing_nullable=True,
        )

    with op.batch_alter_table("habitos", schema=None) as batch_op:
        batch_op.alter_column(
            "cantidad_objetivo",
            existing_type=sa.Numeric(8, 2),
            type_=sa.Integer(),
            existing_nullable=True,
        )
