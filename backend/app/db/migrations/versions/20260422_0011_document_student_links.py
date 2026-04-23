"""document links for multiple students

Revision ID: 20260422_0011
Revises: 20260422_0010
Create Date: 2026-04-22 23:55:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260422_0011"
down_revision: Union[str, Sequence[str], None] = "20260422_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "stored_document_student_links" not in table_names:
        op.create_table(
            "stored_document_student_links",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("document_id", sa.Integer(), sa.ForeignKey("stored_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("document_id", "student_id", name="uq_document_student_link"),
        )

    # Backfill current student-owned documents to preserve behavior.
    if "stored_document_student_links" in set(sa.inspect(bind).get_table_names()):
        op.execute(
            sa.text(
                """
                INSERT INTO stored_document_student_links (document_id, student_id, created_at, updated_at)
                SELECT d.id, d.owner_id, now(), now()
                FROM stored_documents d
                LEFT JOIN stored_document_student_links l
                  ON l.document_id = d.id AND l.student_id = d.owner_id
                WHERE d.owner_type = 'student' AND l.id IS NULL
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "stored_document_student_links" in table_names:
        op.drop_table("stored_document_student_links")
