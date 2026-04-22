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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    assignment_columns = {column["name"] for column in inspector.get_columns("assignments")}
    if "display_order" not in assignment_columns:
        op.add_column("assignments", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
        op.alter_column("assignments", "display_order", server_default=None)

    if not inspector.has_table("gradebook_calculated_columns"):
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
        op.alter_column("gradebook_calculated_columns", "display_order", server_default=None)

    index_name = op.f("ix_gradebook_calculated_columns_course_id")
    existing_indexes = {index["name"] for index in inspector.get_indexes("gradebook_calculated_columns")}
    if index_name not in existing_indexes:
        op.create_index(
            index_name,
            "gradebook_calculated_columns",
            ["course_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("gradebook_calculated_columns"):
        index_name = op.f("ix_gradebook_calculated_columns_course_id")
        existing_indexes = {index["name"] for index in inspector.get_indexes("gradebook_calculated_columns")}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="gradebook_calculated_columns")
        op.drop_table("gradebook_calculated_columns")

    assignment_columns = {column["name"] for column in inspector.get_columns("assignments")}
    if "display_order" in assignment_columns:
        op.drop_column("assignments", "display_order")
