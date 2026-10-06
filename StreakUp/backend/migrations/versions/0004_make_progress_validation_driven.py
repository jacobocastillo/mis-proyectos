"""Make progress validation-driven.

Revision ID: 0004_make_progress_validation_driven
Revises: 0003_add_habit_configuration_fields
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_make_progress_validation_driven"
down_revision = "0003_add_habit_configuration_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("validaciones", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.create_check_constraint(
            "ck_validaciones_status",
            "status IN ('pending','approved','rejected')",
        )

    op.execute(
        """
        UPDATE validaciones
        SET status = CASE
            WHEN validado = true THEN 'approved'
            ELSE 'rejected'
        END
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("validaciones", schema=None) as batch_op:
        batch_op.drop_constraint("ck_validaciones_status", type_="check")
        batch_op.drop_column("status")
