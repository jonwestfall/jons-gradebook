from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class MeetingMode(str, enum.Enum):
    in_person = "in_person"
    virtual = "virtual"
    phone = "phone"
    other = "other"


class Advisee(Base, TimestampMixin):
    __tablename__ = "advisees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("student_profiles.id", ondelete="SET NULL"))
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    external_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    meetings = relationship("AdvisingMeeting", back_populates="advisee", cascade="all, delete-orphan")


class AdvisingMeeting(Base, TimestampMixin):
    __tablename__ = "advising_meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    advisee_id: Mapped[int] = mapped_column(ForeignKey("advisees.id", ondelete="CASCADE"), nullable=False)
    meeting_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[MeetingMode] = mapped_column(Enum(MeetingMode), nullable=False, default=MeetingMode.in_person)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    action_items: Mapped[Optional[str]] = mapped_column(Text)

    advisee = relationship("Advisee", back_populates="meetings")
