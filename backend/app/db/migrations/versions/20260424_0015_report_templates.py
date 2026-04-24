"""report templates and runs

Revision ID: 20260424_0015
Revises: 20260424_0014
Create Date: 2026-04-24 14:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260424_0015"
down_revision: Union[str, Sequence[str], None] = "20260424_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


json_type = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "report_templates" not in table_names:
        op.create_table(
            "report_templates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("report_type", sa.String(length=60), nullable=False, server_default="student"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("config_json", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if "report_template_assets" not in table_names:
        op.create_table(
            "report_template_assets",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("template_id", sa.Integer(), sa.ForeignKey("report_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("asset_type", sa.String(length=40), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("mime_type", sa.String(length=120), nullable=False),
            sa.Column("file_path", sa.String(length=1024), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    if "report_runs" not in table_names:
        op.create_table(
            "report_runs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("template_id", sa.Integer(), sa.ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("report_type", sa.String(length=60), nullable=False, server_default="student"),
            sa.Column("filters_json", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("pdf_path", sa.String(length=1024), nullable=False),
            sa.Column("png_path", sa.String(length=1024), nullable=False),
            sa.Column("pdf_document_id", sa.Integer(), sa.ForeignKey("stored_documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("png_document_id", sa.Integer(), sa.ForeignKey("stored_documents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_report_runs_student_id", "report_runs", ["student_id"])
        op.create_index("ix_report_runs_template_id", "report_runs", ["template_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "report_runs" in table_names:
        op.drop_index("ix_report_runs_template_id", table_name="report_runs")
        op.drop_index("ix_report_runs_student_id", table_name="report_runs")
        op.drop_table("report_runs")
    if "report_template_assets" in table_names:
        op.drop_table("report_template_assets")
    if "report_templates" in table_names:
        op.drop_table("report_templates")
