"""student profile alerts and tags

Revision ID: 20260421_0003
Revises: 20260421_0002
Create Date: 2026-04-21 19:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260421_0003"
down_revision: Union[str, Sequence[str], None] = "20260421_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("severity IN ('high', 'medium', 'low')", name="ck_student_alerts_severity"),
        sa.CheckConstraint("status IN ('active', 'resolved')", name="ck_student_alerts_status"),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_student_alerts_student_id"), "student_alerts", ["student_id"], unique=False)

    op.create_table(
        "student_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_student_tags_name"), "student_tags", ["name"], unique=True)

    op.create_table(
        "student_profile_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["student_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "tag_id", name="uq_student_profile_tag"),
    )
    op.create_index(op.f("ix_student_profile_tags_student_id"), "student_profile_tags", ["student_id"], unique=False)
    op.create_index(op.f("ix_student_profile_tags_tag_id"), "student_profile_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_student_profile_tags_tag_id"), table_name="student_profile_tags")
    op.drop_index(op.f("ix_student_profile_tags_student_id"), table_name="student_profile_tags")
    op.drop_table("student_profile_tags")

    op.drop_index(op.f("ix_student_tags_name"), table_name="student_tags")
    op.drop_table("student_tags")

    op.drop_index(op.f("ix_student_alerts_student_id"), table_name="student_alerts")
    op.drop_table("student_alerts")
