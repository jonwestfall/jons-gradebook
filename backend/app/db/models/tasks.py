from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"
    canceled = "canceled"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.open
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False), nullable=False, default=TaskPriority.medium
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    note: Mapped[Optional[str]] = mapped_column(Text)
    linked_student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("student_profiles.id", ondelete="SET NULL"), index=True)
    linked_course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    linked_interaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("interaction_logs.id", ondelete="SET NULL"), index=True)
    linked_advising_meeting_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("advising_meetings.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[str] = mapped_column(String(60), nullable=False, default="manual")
    outcome_tag: Mapped[Optional[str]] = mapped_column(String(80))
    outcome_note: Mapped[Optional[str]] = mapped_column(Text)

    linked_student = relationship("StudentProfile")
    linked_course = relationship("Course")
    linked_interaction = relationship("InteractionLog")
    linked_advising_meeting = relationship("AdvisingMeeting")


class WorkflowBenchmarkEvent(Base, TimestampMixin):
    __tablename__ = "workflow_benchmark_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    context_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
