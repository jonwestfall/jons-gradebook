from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.common import Base, TimestampMixin


class BackupArtifact(Base, TimestampMixin):
    __tablename__ = "backup_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backup_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[Optional[str]] = mapped_column(Text)
