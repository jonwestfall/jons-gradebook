"""v2 closeout conflicts benchmarks and governance

Revision ID: 20260425_0017
Revises: 20260424_0016
Create Date: 2026-04-25 12:45:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260425_0017"
down_revision: Union[str, Sequence[str], None] = "20260424_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = postgresql.JSONB(astext_type=sa.Text())


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "canvas_sync_conflicts" not in table_names:
        op.create_table(
            "canvas_sync_conflicts",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("sync_run_id", sa.Integer(), sa.ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("grade_entry_id", sa.Integer(), sa.ForeignKey("grade_entries.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "submission_snapshot_id",
                sa.Integer(),
                sa.ForeignKey("canvas_submission_snapshots.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("canvas_course_id", sa.String(length=64), nullable=True),
            sa.Column("canvas_assignment_id", sa.String(length=64), nullable=True),
            sa.Column("canvas_user_id", sa.String(length=64), nullable=True),
            sa.Column("local_score", sa.Float(), nullable=True),
            sa.Column("canvas_score", sa.Float(), nullable=True),
            sa.Column("local_status", sa.String(length=40), nullable=True),
            sa.Column("canvas_status", sa.String(length=40), nullable=True),
            sa.Column("local_source", sa.String(length=40), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
            sa.Column("rationale", sa.Text(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        for name, columns in {
            "ix_canvas_sync_conflicts_course_id": ["course_id"],
            "ix_canvas_sync_conflicts_assignment_id": ["assignment_id"],
            "ix_canvas_sync_conflicts_student_id": ["student_id"],
            "ix_canvas_sync_conflicts_grade_entry_id": ["grade_entry_id"],
            "ix_canvas_sync_conflicts_canvas_course_id": ["canvas_course_id"],
            "ix_canvas_sync_conflicts_canvas_assignment_id": ["canvas_assignment_id"],
            "ix_canvas_sync_conflicts_canvas_user_id": ["canvas_user_id"],
        }.items():
            op.create_index(name, "canvas_sync_conflicts", columns)

    if "tasks" in table_names:
        columns = _columns(inspector, "tasks")
        if "outcome_tag" not in columns:
            op.add_column("tasks", sa.Column("outcome_tag", sa.String(length=80), nullable=True))
        if "outcome_note" not in columns:
            op.add_column("tasks", sa.Column("outcome_note", sa.Text(), nullable=True))

    if "workflow_benchmark_events" not in table_names:
        op.create_table(
            "workflow_benchmark_events",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("workflow", sa.String(length=80), nullable=False),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("context_json", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_workflow_benchmark_events_workflow", "workflow_benchmark_events", ["workflow"])

    if "llm_instruction_templates" in table_names:
        columns = _columns(inspector, "llm_instruction_templates")
        if "version" not in columns:
            op.add_column("llm_instruction_templates", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        if "approval_status" not in columns:
            op.add_column(
                "llm_instruction_templates",
                sa.Column("approval_status", sa.String(length=40), nullable=False, server_default="draft"),
            )
        if "approval_note" not in columns:
            op.add_column("llm_instruction_templates", sa.Column("approval_note", sa.Text(), nullable=True))
        if "approved_at" not in columns:
            op.add_column("llm_instruction_templates", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        if "parent_template_id" not in columns:
            op.add_column("llm_instruction_templates", sa.Column("parent_template_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                "fk_llm_instruction_templates_parent_template_id",
                "llm_instruction_templates",
                "llm_instruction_templates",
                ["parent_template_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "policy_pack" not in columns:
            op.add_column("llm_instruction_templates", sa.Column("policy_pack", sa.String(length=120), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "llm_instruction_templates" in table_names:
        columns = _columns(inspector, "llm_instruction_templates")
        for column_name in ["policy_pack", "approved_at", "approval_note", "approval_status", "version"]:
            if column_name in columns:
                op.drop_column("llm_instruction_templates", column_name)
        if "parent_template_id" in columns:
            op.drop_constraint(
                "fk_llm_instruction_templates_parent_template_id",
                "llm_instruction_templates",
                type_="foreignkey",
            )
            op.drop_column("llm_instruction_templates", "parent_template_id")

    if "workflow_benchmark_events" in table_names:
        op.drop_index("ix_workflow_benchmark_events_workflow", table_name="workflow_benchmark_events")
        op.drop_table("workflow_benchmark_events")

    if "tasks" in table_names:
        columns = _columns(inspector, "tasks")
        if "outcome_note" in columns:
            op.drop_column("tasks", "outcome_note")
        if "outcome_tag" in columns:
            op.drop_column("tasks", "outcome_tag")

    if "canvas_sync_conflicts" in table_names:
        for index_name in [
            "ix_canvas_sync_conflicts_canvas_user_id",
            "ix_canvas_sync_conflicts_canvas_assignment_id",
            "ix_canvas_sync_conflicts_canvas_course_id",
            "ix_canvas_sync_conflicts_grade_entry_id",
            "ix_canvas_sync_conflicts_student_id",
            "ix_canvas_sync_conflicts_assignment_id",
            "ix_canvas_sync_conflicts_course_id",
        ]:
            indexes = {idx["name"] for idx in inspector.get_indexes("canvas_sync_conflicts")}
            if index_name in indexes:
                op.drop_index(index_name, table_name="canvas_sync_conflicts")
        op.drop_table("canvas_sync_conflicts")
