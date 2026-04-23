"""tasks and grade entry audit tables

Revision ID: 20260423_0013
Revises: 20260423_0012
Create Date: 2026-04-23 12:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260423_0013"
down_revision: Union[str, Sequence[str], None] = "20260423_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "tasks" not in table_names:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(length=24), nullable=False, server_default="medium"),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("linked_student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="SET NULL")),
            sa.Column("linked_course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="SET NULL")),
            sa.Column("linked_interaction_id", sa.Integer(), sa.ForeignKey("interaction_logs.id", ondelete="SET NULL")),
            sa.Column(
                "linked_advising_meeting_id",
                sa.Integer(),
                sa.ForeignKey("advising_meetings.id", ondelete="SET NULL"),
            ),
            sa.Column("source", sa.String(length=60), nullable=False, server_default="manual"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_tasks_linked_student_id", "tasks", ["linked_student_id"])
        op.create_index("ix_tasks_linked_course_id", "tasks", ["linked_course_id"])
        op.create_index("ix_tasks_linked_interaction_id", "tasks", ["linked_interaction_id"])
        op.create_index("ix_tasks_linked_advising_meeting_id", "tasks", ["linked_advising_meeting_id"])

    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "grade_entry_audits" not in table_names:
        op.create_table(
            "grade_entry_audits",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("grade_entry_id", sa.Integer(), sa.ForeignKey("grade_entries.id", ondelete="SET NULL")),
            sa.Column("action", sa.String(length=40), nullable=False, server_default="upsert"),
            sa.Column("before_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("after_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("was_undone", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_grade_entry_audits_course_id", "grade_entry_audits", ["course_id"])
        op.create_index("ix_grade_entry_audits_assignment_id", "grade_entry_audits", ["assignment_id"])
        op.create_index("ix_grade_entry_audits_student_id", "grade_entry_audits", ["student_id"])
        op.create_index("ix_grade_entry_audits_grade_entry_id", "grade_entry_audits", ["grade_entry_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "grade_entry_audits" in table_names:
        for index_name in [
            "ix_grade_entry_audits_course_id",
            "ix_grade_entry_audits_assignment_id",
            "ix_grade_entry_audits_student_id",
            "ix_grade_entry_audits_grade_entry_id",
        ]:
            indexes = {idx["name"] for idx in inspector.get_indexes("grade_entry_audits")}
            if index_name in indexes:
                op.drop_index(index_name, table_name="grade_entry_audits")
        op.drop_table("grade_entry_audits")

    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "tasks" in table_names:
        for index_name in [
            "ix_tasks_linked_student_id",
            "ix_tasks_linked_course_id",
            "ix_tasks_linked_interaction_id",
            "ix_tasks_linked_advising_meeting_id",
        ]:
            indexes = {idx["name"] for idx in inspector.get_indexes("tasks")}
            if index_name in indexes:
                op.drop_index(index_name, table_name="tasks")
        op.drop_table("tasks")
