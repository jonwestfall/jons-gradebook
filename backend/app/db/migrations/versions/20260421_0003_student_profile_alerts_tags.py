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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("student_alerts"):
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
    alert_indexes = {index["name"] for index in inspector.get_indexes("student_alerts")}
    alert_index = op.f("ix_student_alerts_student_id")
    if alert_index not in alert_indexes:
        op.create_index(alert_index, "student_alerts", ["student_id"], unique=False)

    if not inspector.has_table("student_tags"):
        op.create_table(
            "student_tags",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    tag_indexes = {index["name"] for index in inspector.get_indexes("student_tags")}
    tag_index = op.f("ix_student_tags_name")
    if tag_index not in tag_indexes:
        op.create_index(tag_index, "student_tags", ["name"], unique=True)

    if not inspector.has_table("student_profile_tags"):
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
    profile_tag_indexes = {index["name"] for index in inspector.get_indexes("student_profile_tags")}
    profile_student_index = op.f("ix_student_profile_tags_student_id")
    profile_tag_index = op.f("ix_student_profile_tags_tag_id")
    if profile_student_index not in profile_tag_indexes:
        op.create_index(profile_student_index, "student_profile_tags", ["student_id"], unique=False)
    if profile_tag_index not in profile_tag_indexes:
        op.create_index(profile_tag_index, "student_profile_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("student_profile_tags"):
        profile_tag_indexes = {index["name"] for index in inspector.get_indexes("student_profile_tags")}
        profile_tag_index = op.f("ix_student_profile_tags_tag_id")
        profile_student_index = op.f("ix_student_profile_tags_student_id")
        if profile_tag_index in profile_tag_indexes:
            op.drop_index(profile_tag_index, table_name="student_profile_tags")
        if profile_student_index in profile_tag_indexes:
            op.drop_index(profile_student_index, table_name="student_profile_tags")
        op.drop_table("student_profile_tags")

    if inspector.has_table("student_tags"):
        tag_indexes = {index["name"] for index in inspector.get_indexes("student_tags")}
        tag_index = op.f("ix_student_tags_name")
        if tag_index in tag_indexes:
            op.drop_index(tag_index, table_name="student_tags")
        op.drop_table("student_tags")

    if inspector.has_table("student_alerts"):
        alert_indexes = {index["name"] for index in inspector.get_indexes("student_alerts")}
        alert_index = op.f("ix_student_alerts_student_id")
        if alert_index in alert_indexes:
            op.drop_index(alert_index, table_name="student_alerts")
        op.drop_table("student_alerts")
