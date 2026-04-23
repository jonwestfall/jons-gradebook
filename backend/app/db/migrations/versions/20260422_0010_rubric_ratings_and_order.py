"""rubric ratings and ordering support

Revision ID: 20260422_0010
Revises: 20260422_0009
Create Date: 2026-04-22 23:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260422_0010"
down_revision: Union[str, Sequence[str], None] = "20260422_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    rubric_criteria_cols = {column["name"] for column in inspector.get_columns("rubric_criteria")}
    if "display_order" not in rubric_criteria_cols:
        op.add_column(
            "rubric_criteria",
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        )

    table_names = set(inspector.get_table_names())
    if "rubric_criterion_ratings" not in table_names:
        op.create_table(
            "rubric_criterion_ratings",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("criterion_id", sa.Integer(), sa.ForeignKey("rubric_criteria.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("points", sa.Float(), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    inspector = sa.inspect(bind)
    eval_item_cols = {column["name"] for column in inspector.get_columns("rubric_evaluation_items")}
    if "rating_id" not in eval_item_cols:
        op.add_column(
            "rubric_evaluation_items",
            sa.Column("rating_id", sa.Integer(), sa.ForeignKey("rubric_criterion_ratings.id", ondelete="SET NULL"), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    eval_item_cols = {column["name"] for column in inspector.get_columns("rubric_evaluation_items")}
    if "rating_id" in eval_item_cols:
        op.drop_column("rubric_evaluation_items", "rating_id")

    table_names = set(inspector.get_table_names())
    if "rubric_criterion_ratings" in table_names:
        op.drop_table("rubric_criterion_ratings")

    rubric_criteria_cols = {column["name"] for column in inspector.get_columns("rubric_criteria")}
    if "display_order" in rubric_criteria_cols:
        op.drop_column("rubric_criteria", "display_order")
