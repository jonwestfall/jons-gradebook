"""gradebook local editing fields

Revision ID: 20260422_0006
Revises: 20260422_0005
Create Date: 2026-04-22 14:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260422_0006"
down_revision: Union[str, Sequence[str], None] = "20260422_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


assignment_grading_type = sa.Enum("points", "letter", "completion", name="assignmentgradingtype")
completion_status = sa.Enum("complete", "incomplete", "missing", "excused", name="completionstatus")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    assignment_grading_type.create(bind, checkfirst=True)
    completion_status.create(bind, checkfirst=True)

    assignment_columns = {column["name"] for column in inspector.get_columns("assignments")}
    if "grading_type" not in assignment_columns:
        op.add_column(
            "assignments",
            sa.Column("grading_type", assignment_grading_type, nullable=False, server_default="points"),
        )
        op.alter_column("assignments", "grading_type", server_default=None)

    grade_entry_columns = {column["name"] for column in inspector.get_columns("grade_entries")}
    if "letter_grade" not in grade_entry_columns:
        op.add_column("grade_entries", sa.Column("letter_grade", sa.String(length=16), nullable=True))
    if "completion_status" not in grade_entry_columns:
        op.add_column("grade_entries", sa.Column("completion_status", completion_status, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    grade_entry_columns = {column["name"] for column in inspector.get_columns("grade_entries")}
    if "completion_status" in grade_entry_columns:
        op.drop_column("grade_entries", "completion_status")
    if "letter_grade" in grade_entry_columns:
        op.drop_column("grade_entries", "letter_grade")

    assignment_columns = {column["name"] for column in inspector.get_columns("assignments")}
    if "grading_type" in assignment_columns:
        op.drop_column("assignments", "grading_type")

    bind = op.get_bind()
    completion_status.drop(bind, checkfirst=True)
    assignment_grading_type.drop(bind, checkfirst=True)
