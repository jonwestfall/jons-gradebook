"""sync events and assignment match decisions

Revision ID: 20260422_0005
Revises: 20260421_0004
Create Date: 2026-04-22 08:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260422_0005"
down_revision: Union[str, Sequence[str], None] = "20260421_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignment_match_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("suggestion_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.Enum("confirm_canvas", "reject", name="matchdecisionaction"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["suggestion_id"], ["assignment_match_suggestions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assignment_match_decisions_suggestion_id"),
        "assignment_match_decisions",
        ["suggestion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_match_decisions_course_id"),
        "assignment_match_decisions",
        ["course_id"],
        unique=False,
    )

    op.create_table(
        "canvas_sync_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.Enum("course", "enrollment", "assignment", "submission", name="canvassyncentitytype"), nullable=False),
        sa.Column("action", sa.Enum("created", "updated", "deleted", "unchanged", name="canvassynceventaction"), nullable=False),
        sa.Column("canvas_course_id", sa.String(length=64), nullable=True),
        sa.Column("canvas_item_id", sa.String(length=64), nullable=True),
        sa.Column("local_item_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["sync_run_id"], ["canvas_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_canvas_sync_events_canvas_course_id"), "canvas_sync_events", ["canvas_course_id"], unique=False)
    op.create_index(op.f("ix_canvas_sync_events_canvas_item_id"), "canvas_sync_events", ["canvas_item_id"], unique=False)
    op.create_index(op.f("ix_canvas_sync_events_local_item_id"), "canvas_sync_events", ["local_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_canvas_sync_events_local_item_id"), table_name="canvas_sync_events")
    op.drop_index(op.f("ix_canvas_sync_events_canvas_item_id"), table_name="canvas_sync_events")
    op.drop_index(op.f("ix_canvas_sync_events_canvas_course_id"), table_name="canvas_sync_events")
    op.drop_table("canvas_sync_events")

    op.drop_index(op.f("ix_assignment_match_decisions_course_id"), table_name="assignment_match_decisions")
    op.drop_index(op.f("ix_assignment_match_decisions_suggestion_id"), table_name="assignment_match_decisions")
    op.drop_table("assignment_match_decisions")

    op.execute("DROP TYPE IF EXISTS canvassynceventaction")
    op.execute("DROP TYPE IF EXISTS canvassyncentitytype")
    op.execute("DROP TYPE IF EXISTS matchdecisionaction")
