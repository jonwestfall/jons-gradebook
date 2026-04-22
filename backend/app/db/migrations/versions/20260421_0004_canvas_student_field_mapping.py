"""canvas student field mapping

Revision ID: 20260421_0004
Revises: 20260421_0003
Create Date: 2026-04-21 20:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260421_0004"
down_revision: Union[str, Sequence[str], None] = "20260421_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canvas_student_field_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_field", sa.String(length=64), nullable=False),
        sa.Column("source_paths", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_field"),
    )
    op.create_index(
        op.f("ix_canvas_student_field_mappings_target_field"),
        "canvas_student_field_mappings",
        ["target_field"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_canvas_student_field_mappings_target_field"), table_name="canvas_student_field_mappings")
    op.drop_table("canvas_student_field_mappings")
