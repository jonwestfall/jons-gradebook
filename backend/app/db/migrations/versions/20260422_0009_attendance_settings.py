"""attendance settings per course

Revision ID: 20260422_0009
Revises: 20260422_0008
Create Date: 2026-04-22 22:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260422_0009"
down_revision: Union[str, Sequence[str], None] = "20260422_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("courses")}

    if "attendance_lateness_weight" not in columns:
        op.add_column(
            "courses",
            sa.Column("attendance_lateness_weight", sa.Float(), nullable=False, server_default="0.8"),
        )
    if "attendance_excluded_from_final_grade" not in columns:
        op.add_column(
            "courses",
            sa.Column(
                "attendance_excluded_from_final_grade",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("courses")}

    if "attendance_excluded_from_final_grade" in columns:
        op.drop_column("courses", "attendance_excluded_from_final_grade")
    if "attendance_lateness_weight" in columns:
        op.drop_column("courses", "attendance_lateness_weight")
