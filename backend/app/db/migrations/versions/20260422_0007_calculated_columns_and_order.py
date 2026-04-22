"""calculated columns and column ordering

Revision ID: 20260422_0007
Revises: 20260422_0006
Create Date: 2026-04-22 15:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260422_0007"
down_revision: Union[str, Sequence[str], None] = "20260422_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("assignments", "display_order", server_default=None)

    op.create_table(
        "gradebook_calculated_columns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("assignment_ids", sa.JSON(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "operation IN ('average_percent', 'sum_points', 'completion_rate')",
            name="ck_gradebook_calculated_columns_operation",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_gradebook_calculated_columns_course_id"),
        "gradebook_calculated_columns",
        ["course_id"],
        unique=False,
    )
    op.alter_column("gradebook_calculated_columns", "display_order", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_gradebook_calculated_columns_course_id"), table_name="gradebook_calculated_columns")
    op.drop_table("gradebook_calculated_columns")

    op.drop_column("assignments", "display_order")
