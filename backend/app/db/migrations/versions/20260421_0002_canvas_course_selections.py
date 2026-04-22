"""canvas course selections

Revision ID: 20260421_0002
Revises: 20260421_0001
Create Date: 2026-04-21 18:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260421_0002"
down_revision: Union[str, Sequence[str], None] = "20260421_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("canvas_course_selections"):
        op.create_table(
            "canvas_course_selections",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("canvas_course_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("course_code", sa.String(length=255), nullable=True),
            sa.Column("term_name", sa.String(length=255), nullable=True),
            sa.Column("term_start_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("term_end_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("canvas_course_id"),
        )

    existing_index_names = {index["name"] for index in inspector.get_indexes("canvas_course_selections")}
    index_name = op.f("ix_canvas_course_selections_canvas_course_id")
    if index_name not in existing_index_names:
        op.create_index(
            index_name,
            "canvas_course_selections",
            ["canvas_course_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("canvas_course_selections"):
        return

    existing_index_names = {index["name"] for index in inspector.get_indexes("canvas_course_selections")}
    index_name = op.f("ix_canvas_course_selections_canvas_course_id")
    if index_name in existing_index_names:
        op.drop_index(index_name, table_name="canvas_course_selections")
    op.drop_table("canvas_course_selections")
