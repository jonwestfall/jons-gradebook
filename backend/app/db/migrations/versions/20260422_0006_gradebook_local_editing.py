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
    assignment_grading_type.create(bind, checkfirst=True)
    completion_status.create(bind, checkfirst=True)

    op.add_column(
        "assignments",
        sa.Column("grading_type", assignment_grading_type, nullable=False, server_default="points"),
    )
    op.add_column("grade_entries", sa.Column("letter_grade", sa.String(length=16), nullable=True))
    op.add_column("grade_entries", sa.Column("completion_status", completion_status, nullable=True))

    op.alter_column("assignments", "grading_type", server_default=None)


def downgrade() -> None:
    op.drop_column("grade_entries", "completion_status")
    op.drop_column("grade_entries", "letter_grade")
    op.drop_column("assignments", "grading_type")

    bind = op.get_bind()
    completion_status.drop(bind, checkfirst=True)
    assignment_grading_type.drop(bind, checkfirst=True)
