from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.common import Base, TimestampMixin


class AppOption(Base, TimestampMixin):
    __tablename__ = "app_options"
    __table_args__ = (UniqueConstraint("key", name="uq_app_option_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
