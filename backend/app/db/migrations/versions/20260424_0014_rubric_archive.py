"""rubric archive support

Revision ID: 20260424_0014
Revises: 20260423_0013
Create Date: 2026-04-24 09:35:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260424_0014"
down_revision: Union[str, Sequence[str], None] = "20260423_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "rubric_templates" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("rubric_templates")}
    if "archived_at" not in columns:
        op.add_column("rubric_templates", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "rubric_templates" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("rubric_templates")}
    if "archived_at" in columns:
        op.drop_column("rubric_templates", "archived_at")
