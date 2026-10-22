"""reconcile schema drift between migrations and models

Revision ID: 20261022_0018
Revises: 20260425_0017
Create Date: 2026-10-22 12:00:00

Revision 20260421_0001 used to call Base.metadata.create_all() with the live
models, so existing databases were built from whichever model version was
current when they were first created, and later revisions skipped the tables
that already existed. Depending on install date, the same column can therefore
be JSON or JSONB, a string-backed enum can be VARCHAR(15) or VARCHAR(40), and
some indexes or unique constraints may or may not exist.

This revision inspects the live schema and converges every database on the
shape declared by the models. Each step is a no-op when the database already
matches, so it is safe on fresh installs and on every historical install.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261022_0018"
down_revision: Union[str, Sequence[str], None] = "20260425_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, target type keyword)
JSON_COLUMNS = [
    ("app_options", "value_json", "jsonb"),
    ("llm_workbench_jobs", "metadata_json", "json"),
    ("workflow_benchmark_events", "context_json", "json"),
]

# String-backed (non-native) enum columns and the VARCHAR length the models declare.
ENUM_VARCHAR_LENGTHS = [
    ("student_alerts", "severity", 16),
    ("student_alerts", "status", 16),
    ("tasks", "status", 24),
    ("tasks", "priority", 24),
    ("gradebook_calculated_columns", "operation", 32),
    ("canvas_sync_conflicts", "status", 40),
]

# Indexes declared with index=True on the models: (index name, table, columns).
INDEXES = [
    ("ix_llm_workbench_jobs_student_profile_id", "llm_workbench_jobs", ["student_profile_id"]),
    ("ix_llm_workbench_jobs_source_document_id", "llm_workbench_jobs", ["source_document_id"]),
    ("ix_report_runs_student_id", "report_runs", ["student_id"]),
    ("ix_report_runs_template_id", "report_runs", ["template_id"]),
]

# Unique constraints that duplicate a unique index the models already declare:
# (table, column, unique index that must remain).
REDUNDANT_UNIQUE_CONSTRAINTS = [
    ("canvas_course_selections", "canvas_course_id", "ix_canvas_course_selections_canvas_course_id"),
    ("canvas_student_field_mappings", "target_field", "ix_canvas_student_field_mappings_target_field"),
    ("student_tags", "name", "ix_student_tags_name"),
]


def _column(inspector: sa.Inspector, table_name: str, column_name: str) -> dict | None:
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return column
    return None


def _reconcile_json_column(inspector: sa.Inspector, table_name: str, column_name: str, target: str) -> None:
    column = _column(inspector, table_name, column_name)
    if column is None:
        return
    is_jsonb = isinstance(column["type"], postgresql.JSONB)
    if (target == "jsonb") == is_jsonb:
        return

    default = column.get("default")
    if default is not None:
        op.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" DROP DEFAULT')
    op.execute(
        f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" TYPE {target} USING "{column_name}"::text::{target}'
    )
    if default is not None:
        # Defaults in this schema are literal JSON values such as '{}'::jsonb; re-cast them.
        literal = default.split("::")[0]
        op.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" SET DEFAULT {literal}::{target}')


def _widen_varchar(inspector: sa.Inspector, table_name: str, column_name: str, length: int) -> None:
    column = _column(inspector, table_name, column_name)
    if column is None:
        return
    current_length = getattr(column["type"], "length", None)
    if current_length is None or current_length >= length:
        return
    op.alter_column(
        table_name,
        column_name,
        type_=sa.String(length=length),
        existing_type=column["type"],
        existing_nullable=column["nullable"],
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    for table_name, column_name, target in JSON_COLUMNS:
        if table_name in table_names:
            _reconcile_json_column(inspector, table_name, column_name, target)

    for table_name, column_name, length in ENUM_VARCHAR_LENGTHS:
        if table_name in table_names:
            _widen_varchar(inspector, table_name, column_name, length)

    for index_name, table_name, columns in INDEXES:
        if table_name not in table_names:
            continue
        existing = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name not in existing:
            op.create_index(index_name, table_name, columns)

    for table_name, column_name, unique_index_name in REDUNDANT_UNIQUE_CONSTRAINTS:
        if table_name not in table_names:
            continue
        unique_indexes = {index["name"] for index in inspector.get_indexes(table_name) if index.get("unique")}
        if unique_index_name not in unique_indexes:
            # Only drop the constraint when the unique index keeps enforcing uniqueness.
            continue
        for constraint in inspector.get_unique_constraints(table_name):
            if constraint["column_names"] == [column_name] and constraint["name"]:
                op.drop_constraint(constraint["name"], table_name, type_="unique")


def downgrade() -> None:
    # This revision converges divergent historical schemas onto one shape, so there is
    # no single prior state to restore. The reconciled schema is compatible with the
    # code at revision 20260425_0017, so downgrading is intentionally a no-op.
    pass
