"""settings options and document category

Revision ID: 20260423_0012
Revises: 20260422_0011
Create Date: 2026-04-23 08:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260423_0012"
down_revision: Union[str, Sequence[str], None] = "20260422_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "app_options" not in table_names:
        op.create_table(
            "app_options",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("key", sa.String(length=120), nullable=False),
            sa.Column("value_json", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("key", name="uq_app_option_key"),
        )

    document_columns = {column["name"] for column in inspector.get_columns("stored_documents")}
    if "category" not in document_columns:
        op.add_column(
            "stored_documents",
            sa.Column("category", sa.String(length=80), nullable=False, server_default="Other"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    document_columns = {column["name"] for column in inspector.get_columns("stored_documents")}
    if "category" in document_columns:
        op.drop_column("stored_documents", "category")

    table_names = set(inspector.get_table_names())
    if "app_options" in table_names:
        op.drop_table("app_options")
