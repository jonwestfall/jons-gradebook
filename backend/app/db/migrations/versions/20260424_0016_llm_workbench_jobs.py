"""llm workbench jobs and instruction templates

Revision ID: 20260424_0016
Revises: 20260424_0015
Create Date: 2026-04-24 16:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260424_0016"
down_revision: Union[str, Sequence[str], None] = "20260424_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    llm_run_columns = {column["name"] for column in inspector.get_columns("llm_runs")} if "llm_runs" in table_names else set()
    if "llm_runs" in table_names and "deidentify_map_encrypted" not in llm_run_columns:
        op.add_column("llm_runs", sa.Column("deidentify_map_encrypted", sa.Text(), nullable=True))

    if "llm_instruction_templates" not in table_names:
        op.create_table(
            "llm_instruction_templates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("task_type", sa.String(length=80), nullable=False, server_default="feedback"),
            sa.Column("instructions", sa.Text(), nullable=False),
            sa.Column("output_guidance", sa.Text(), nullable=True),
            sa.Column("rubric_guidance", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if "llm_workbench_jobs" not in table_names:
        op.create_table(
            "llm_workbench_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("student_profile_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_document_id", sa.Integer(), sa.ForeignKey("stored_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("instruction_template_id", sa.Integer(), sa.ForeignKey("llm_instruction_templates.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("rubric_id", sa.Integer(), sa.ForeignKey("rubric_templates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("llm_run_id", sa.Integer(), sa.ForeignKey("llm_runs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("final_document_id", sa.Integer(), sa.ForeignKey("stored_documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column(
                "provider",
                postgresql.ENUM("openai", "ollama", "gemini", name="llmprovider", create_type=False),
                nullable=False,
                server_default="ollama",
            ),
            sa.Column("model", sa.String(length=120), nullable=False, server_default="llama3.1"),
            sa.Column(
                "status",
                sa.Enum("draft", "prompt_ready", "output_ready", "final_ready", "finalized", "failed", name="llmworkbenchjobstatus"),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("final_feedback_encrypted", sa.Text(), nullable=True),
            sa.Column("metadata_json", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_llm_workbench_jobs_student_profile_id", "llm_workbench_jobs", ["student_profile_id"])
        op.create_index("ix_llm_workbench_jobs_source_document_id", "llm_workbench_jobs", ["source_document_id"])

    op.execute(
        """
        INSERT INTO llm_instruction_templates
            (name, description, task_type, instructions, output_guidance, rubric_guidance, is_active, is_default)
        SELECT seed.name, seed.description, seed.task_type, seed.instructions, seed.output_guidance, seed.rubric_guidance, true, seed.is_default
        FROM (
            VALUES
            (
                'Paper Feedback',
                'Balanced instructor feedback for a submitted paper.',
                'feedback',
                'Read the student work as an instructor. Identify strengths, areas for revision, and concrete next steps. Do not invent facts not present in the work.',
                'Return sections titled Summary, Strengths, Revision Priorities, and Suggested Instructor Feedback.',
                'If rubric criteria are provided, organize feedback under the relevant criteria but do not assign scores.',
                true
            ),
            (
                'Strengths and Growth Areas',
                'Concise formative feedback with encouragement and next actions.',
                'feedback',
                'Provide constructive formative feedback that is specific, kind, and actionable.',
                'Return sections titled What Is Working, Growth Areas, and Next Steps.',
                'Reference rubric criteria only as narrative anchors; do not grade.',
                false
            ),
            (
                'Grammar and Style Review',
                'Writing mechanics and clarity feedback without rewriting the whole paper.',
                'writing_review',
                'Review clarity, organization, grammar, citation hygiene, and academic tone. Avoid changing the student voice.',
                'Return sections titled Clarity, Organization, Mechanics, and Suggested Edits.',
                'Connect writing feedback to rubric criteria when they are relevant.',
                false
            ),
            (
                'Rubric Narrative Prep',
                'Draft criterion-aligned comments for manual rubric entry.',
                'rubric_feedback',
                'Use the supplied rubric as context for narrative feedback. Do not calculate or suggest point values.',
                'Return one narrative paragraph per relevant rubric criterion plus an overall comment.',
                'Use every supplied criterion title as a heading when possible. Do not assign ratings or scores.',
                false
            )
        ) AS seed(name, description, task_type, instructions, output_guidance, rubric_guidance, is_default)
        WHERE NOT EXISTS (
            SELECT 1 FROM llm_instruction_templates existing WHERE existing.name = seed.name
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "llm_workbench_jobs" in table_names:
        op.drop_index("ix_llm_workbench_jobs_source_document_id", table_name="llm_workbench_jobs")
        op.drop_index("ix_llm_workbench_jobs_student_profile_id", table_name="llm_workbench_jobs")
        op.drop_table("llm_workbench_jobs")
    if "llm_instruction_templates" in table_names:
        op.drop_table("llm_instruction_templates")
    if "llm_runs" in table_names:
        run_columns = {column["name"] for column in inspector.get_columns("llm_runs")}
        if "deidentify_map_encrypted" in run_columns:
            op.drop_column("llm_runs", "deidentify_map_encrypted")
