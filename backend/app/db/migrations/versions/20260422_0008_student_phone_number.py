"""add student phone number

Revision ID: 20260422_0008
Revises: 20260422_0007
Create Date: 2026-04-22 21:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260422_0008"
down_revision: Union[str, Sequence[str], None] = "20260422_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("student_profiles")}
    if "phone_number" not in columns:
        op.add_column("student_profiles", sa.Column("phone_number", sa.String(length=32), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("student_profiles")}
    if "phone_number" in columns:
        op.drop_column("student_profiles", "phone_number")
