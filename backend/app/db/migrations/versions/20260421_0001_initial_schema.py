"""initial schema

Revision ID: 20260421_0001
Revises:
Create Date: 2026-04-21 00:00:00

This migration is a frozen snapshot of the schema as it existed when the
project started (commit f9db8f6). It must never import the live ORM models:
later revisions build on top of this exact shape, so changing the models must
not change what this revision creates. The canvas_course_selections table is
owned by revision 20260421_0002.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260421_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ENUM_TYPES = [
    "assignmentsource",
    "attendancestatus",
    "documenttype",
    "enrollmentrole",
    "gradesource",
    "gradestatus",
    "interactiontype",
    "llmprovider",
    "llmrunstatus",
    "matchstatus",
    "meetingmode",
    "rubriccriteriontype",
    "ruletype",
    "syncstatus",
    "synctrigger",
]


def upgrade() -> None:
    op.create_table(
        "backup_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("backup_path", sa.String(length=1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("encrypted", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "canvas_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.Enum("manual", "scheduled", name="synctrigger"), nullable=False),
        sa.Column("status", sa.Enum("started", "completed", "failed", name="syncstatus"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_label", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canvas_course_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("section_name", sa.String(length=255), nullable=True),
        sa.Column("term_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_canvas_course_id"), "courses", ["canvas_course_id"], unique=True)
    op.create_table(
        "grade_rule_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "rule_type", sa.Enum("drop_lowest_in_group", "required_completion_gate", name="ruletype"), nullable=False
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "llm_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.Enum("openai", "ollama", "gemini", name="llmprovider"), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("input_text_encrypted", sa.Text(), nullable=False),
        sa.Column("deidentified_preview", sa.Text(), nullable=False),
        sa.Column("deidentify_map", sa.JSON(), nullable=False),
        sa.Column(
            "status", sa.Enum("draft", "previewed", "sent", "completed", "failed", name="llmrunstatus"), nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rubric_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("max_points", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "stored_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_type", sa.String(length=50), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.Enum("pdf", "docx", "txt", "other", name="documenttype"), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canvas_user_id", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("student_number", sa.String(length=64), nullable=True),
        sa.Column("institution_name", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_student_profiles_canvas_user_id"), "student_profiles", ["canvas_user_id"], unique=True)
    op.create_index(op.f("ix_student_profiles_email"), "student_profiles", ["email"], unique=False)
    op.create_index(op.f("ix_student_profiles_student_number"), "student_profiles", ["student_number"], unique=False)
    op.create_table(
        "advisees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_advisees_external_id"), "advisees", ["external_id"], unique=False)
    op.create_table(
        "assignment_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "name", name="uq_assignment_group_name_course"),
    )
    op.create_table(
        "canvas_assignment_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("canvas_course_id", sa.String(length=64), nullable=False),
        sa.Column("canvas_assignment_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("points_possible", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sync_run_id"], ["canvas_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_canvas_assignment_snapshots_canvas_assignment_id"),
        "canvas_assignment_snapshots",
        ["canvas_assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canvas_assignment_snapshots_canvas_course_id"),
        "canvas_assignment_snapshots",
        ["canvas_course_id"],
        unique=False,
    )
    op.create_table(
        "canvas_course_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("canvas_course_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("section_name", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sync_run_id"], ["canvas_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_canvas_course_snapshots_canvas_course_id"),
        "canvas_course_snapshots",
        ["canvas_course_id"],
        unique=False,
    )
    op.create_table(
        "canvas_enrollment_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("canvas_course_id", sa.String(length=64), nullable=False),
        sa.Column("canvas_enrollment_id", sa.String(length=64), nullable=False),
        sa.Column("canvas_user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sync_run_id"], ["canvas_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_canvas_enrollment_snapshots_canvas_course_id"),
        "canvas_enrollment_snapshots",
        ["canvas_course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canvas_enrollment_snapshots_canvas_enrollment_id"),
        "canvas_enrollment_snapshots",
        ["canvas_enrollment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canvas_enrollment_snapshots_canvas_user_id"),
        "canvas_enrollment_snapshots",
        ["canvas_user_id"],
        unique=False,
    )
    op.create_table(
        "canvas_submission_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=False),
        sa.Column("canvas_course_id", sa.String(length=64), nullable=False),
        sa.Column("canvas_assignment_id", sa.String(length=64), nullable=False),
        sa.Column("canvas_user_id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sync_run_id"], ["canvas_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_canvas_submission_snapshots_canvas_assignment_id"),
        "canvas_submission_snapshots",
        ["canvas_assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canvas_submission_snapshots_canvas_course_id"),
        "canvas_submission_snapshots",
        ["canvas_course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canvas_submission_snapshots_canvas_user_id"),
        "canvas_submission_snapshots",
        ["canvas_user_id"],
        unique=False,
    )
    op.create_table(
        "class_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("room", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "course_grade_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["grade_rule_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "template_id", name="uq_course_rule"),
    )
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("student", "teacher", "ta", name="enrollmentrole"), nullable=False),
        sa.Column("canvas_enrollment_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "student_id", name="uq_enrollment_course_student"),
    )
    op.create_index(op.f("ix_enrollments_canvas_enrollment_id"), "enrollments", ["canvas_enrollment_id"], unique=False)
    op.create_table(
        "llm_outputs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("output_text_encrypted", sa.Text(), nullable=False),
        sa.Column("edited_text_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["llm_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rubric_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "criterion_type", sa.Enum("points", "checkbox", "narrative", name="rubriccriteriontype"), nullable=False
        ),
        sa.Column("max_points", sa.Float(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rubric_id"], ["rubric_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stored_document_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("encrypted_file_path", sa.String(length=1024), nullable=False),
        sa.Column("extracted_text_encrypted", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["stored_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version"),
    )
    op.create_table(
        "advising_meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("advisee_id", sa.Integer(), nullable=False),
        sa.Column("meeting_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.Enum("in_person", "virtual", "phone", "other", name="meetingmode"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("action_items", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["advisee_id"], ["advisees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("assignment_group_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.Enum("canvas", "local", name="assignmentsource"), nullable=False),
        sa.Column("canvas_assignment_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("points_possible", sa.Float(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False),
        sa.Column("hidden_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_group_id"], ["assignment_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assignments_canvas_assignment_id"), "assignments", ["canvas_assignment_id"], unique=False)
    op.create_index(op.f("ix_assignments_course_id"), "assignments", ["course_id"], unique=False)
    op.create_table(
        "class_meetings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("is_generated", sa.Boolean(), nullable=False),
        sa.Column("is_canceled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["class_schedules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "meeting_date", name="uq_class_meeting_date"),
    )
    op.create_table(
        "interaction_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=True),
        sa.Column("advisee_id", sa.Integer(), nullable=True),
        sa.Column(
            "interaction_type",
            sa.Enum(
                "attendance",
                "advising_meeting",
                "office_visit",
                "manual_note",
                "email_log",
                "file_upload",
                name="interactiontype",
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["advisee_id"], ["advisees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assignment_match_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("canvas_assignment_id", sa.Integer(), nullable=False),
        sa.Column("local_assignment_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("name_score", sa.Float(), nullable=False),
        sa.Column("due_date_score", sa.Float(), nullable=False),
        sa.Column("points_score", sa.Float(), nullable=False),
        sa.Column("status", sa.Enum("suggested", "confirmed", "rejected", name="matchstatus"), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["canvas_assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["local_assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id", "canvas_assignment_id", "local_assignment_id", name="uq_assignment_match_triplet"
        ),
    )
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("present", "absent", "tardy", "excused", name="attendancestatus"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["class_meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_id", "student_id", name="uq_attendance_meeting_student"),
    )
    op.create_table(
        "grade_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.Enum("canvas", "local", "manual_override", name="gradesource"), nullable=False),
        sa.Column("status", sa.Enum("graded", "missing", "excused", "unsubmitted", name="gradestatus"), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_run_id"], ["canvas_sync_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "student_id", name="uq_grade_assignment_student"),
    )
    op.create_index(op.f("ix_grade_entries_assignment_id"), "grade_entries", ["assignment_id"], unique=False)
    op.create_index(op.f("ix_grade_entries_student_id"), "grade_entries", ["student_id"], unique=False)
    op.create_table(
        "rubric_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rubric_id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=True),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("evaluator_notes", sa.Text(), nullable=True),
        sa.Column("total_points", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rubric_id"], ["rubric_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rubric_evaluation_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.Column("points_awarded", sa.Float(), nullable=True),
        sa.Column("is_checked", sa.Boolean(), nullable=True),
        sa.Column("narrative_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["criterion_id"], ["rubric_criteria.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["rubric_evaluations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("rubric_evaluation_items")
    op.drop_table("rubric_evaluations")
    op.drop_index(op.f("ix_grade_entries_student_id"), table_name="grade_entries")
    op.drop_index(op.f("ix_grade_entries_assignment_id"), table_name="grade_entries")
    op.drop_table("grade_entries")
    op.drop_table("attendance_records")
    op.drop_table("assignment_match_suggestions")
    op.drop_table("interaction_logs")
    op.drop_table("class_meetings")
    op.drop_index(op.f("ix_assignments_course_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_canvas_assignment_id"), table_name="assignments")
    op.drop_table("assignments")
    op.drop_table("advising_meetings")
    op.drop_table("stored_document_versions")
    op.drop_table("rubric_criteria")
    op.drop_table("llm_outputs")
    op.drop_index(op.f("ix_enrollments_canvas_enrollment_id"), table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_table("course_grade_rules")
    op.drop_table("class_schedules")
    op.drop_index(op.f("ix_canvas_submission_snapshots_canvas_user_id"), table_name="canvas_submission_snapshots")
    op.drop_index(op.f("ix_canvas_submission_snapshots_canvas_course_id"), table_name="canvas_submission_snapshots")
    op.drop_index(op.f("ix_canvas_submission_snapshots_canvas_assignment_id"), table_name="canvas_submission_snapshots")
    op.drop_table("canvas_submission_snapshots")
    op.drop_index(op.f("ix_canvas_enrollment_snapshots_canvas_user_id"), table_name="canvas_enrollment_snapshots")
    op.drop_index(op.f("ix_canvas_enrollment_snapshots_canvas_enrollment_id"), table_name="canvas_enrollment_snapshots")
    op.drop_index(op.f("ix_canvas_enrollment_snapshots_canvas_course_id"), table_name="canvas_enrollment_snapshots")
    op.drop_table("canvas_enrollment_snapshots")
    op.drop_index(op.f("ix_canvas_course_snapshots_canvas_course_id"), table_name="canvas_course_snapshots")
    op.drop_table("canvas_course_snapshots")
    op.drop_index(op.f("ix_canvas_assignment_snapshots_canvas_course_id"), table_name="canvas_assignment_snapshots")
    op.drop_index(op.f("ix_canvas_assignment_snapshots_canvas_assignment_id"), table_name="canvas_assignment_snapshots")
    op.drop_table("canvas_assignment_snapshots")
    op.drop_table("assignment_groups")
    op.drop_index(op.f("ix_advisees_external_id"), table_name="advisees")
    op.drop_table("advisees")
    op.drop_index(op.f("ix_student_profiles_student_number"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_email"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_canvas_user_id"), table_name="student_profiles")
    op.drop_table("student_profiles")
    op.drop_table("stored_documents")
    op.drop_table("rubric_templates")
    op.drop_table("llm_runs")
    op.drop_table("grade_rule_templates")
    op.drop_index(op.f("ix_courses_canvas_course_id"), table_name="courses")
    op.drop_table("courses")
    op.drop_table("canvas_sync_runs")
    op.drop_table("backup_artifacts")
    for enum_name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
