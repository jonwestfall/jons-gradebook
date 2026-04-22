from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class AlertSeverity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class AlertStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"


class StudentAlert(Base, TimestampMixin):
    __tablename__ = "student_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False), nullable=False, default=AlertSeverity.medium
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, native_enum=False), nullable=False, default=AlertStatus.active
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    student = relationship("StudentProfile", back_populates="alerts")


class StudentTag(Base, TimestampMixin):
    __tablename__ = "student_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)

    student_links = relationship("StudentProfileTag", back_populates="tag", cascade="all, delete-orphan")


class StudentProfileTag(Base, TimestampMixin):
    __tablename__ = "student_profile_tags"
    __table_args__ = (UniqueConstraint("student_id", "tag_id", name="uq_student_profile_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("student_tags.id", ondelete="CASCADE"), nullable=False, index=True)

    student = relationship("StudentProfile", back_populates="tag_links")
    tag = relationship("StudentTag", back_populates="student_links")
