from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.common import Base, TimestampMixin


class InteractionType(str, enum.Enum):
    attendance = "attendance"
    advising_meeting = "advising_meeting"
    office_visit = "office_visit"
    manual_note = "manual_note"
    email_log = "email_log"
    file_upload = "file_upload"


class InteractionLog(Base, TimestampMixin):
    __tablename__ = "interaction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("student_profiles.id", ondelete="SET NULL"))
    advisee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("advisees.id", ondelete="SET NULL"))
    interaction_type: Mapped[InteractionType] = mapped_column(Enum(InteractionType), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
