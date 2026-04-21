from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class SyncTrigger(str, enum.Enum):
    manual = "manual"
    scheduled = "scheduled"


class SyncStatus(str, enum.Enum):
    started = "started"
    completed = "completed"
    failed = "failed"


class CanvasSyncRun(Base, TimestampMixin):
    __tablename__ = "canvas_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_type: Mapped[SyncTrigger] = mapped_column(Enum(SyncTrigger), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), nullable=False, default=SyncStatus.started)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    snapshot_label: Mapped[Optional[str]] = mapped_column(String(255))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    course_snapshots = relationship("CanvasCourseSnapshot", back_populates="sync_run", cascade="all, delete-orphan")
    assignment_snapshots = relationship(
        "CanvasAssignmentSnapshot", back_populates="sync_run", cascade="all, delete-orphan"
    )
    enrollment_snapshots = relationship(
        "CanvasEnrollmentSnapshot", back_populates="sync_run", cascade="all, delete-orphan"
    )
    submission_snapshots = relationship(
        "CanvasSubmissionSnapshot", back_populates="sync_run", cascade="all, delete-orphan"
    )


class CanvasCourseSelection(Base, TimestampMixin):
    __tablename__ = "canvas_course_selections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canvas_course_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(String(255))
    term_name: Mapped[Optional[str]] = mapped_column(String(255))
    term_start_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    term_end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_selected: Mapped[bool] = mapped_column(nullable=False, default=False)


class CanvasCourseSnapshot(Base):
    __tablename__ = "canvas_course_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False)
    canvas_course_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_name: Mapped[Optional[str]] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    sync_run = relationship("CanvasSyncRun", back_populates="course_snapshots")


class CanvasAssignmentSnapshot(Base):
    __tablename__ = "canvas_assignment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False)
    canvas_course_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    canvas_assignment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    points_possible: Mapped[Optional[float]] = mapped_column()
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    sync_run = relationship("CanvasSyncRun", back_populates="assignment_snapshots")


class CanvasEnrollmentSnapshot(Base):
    __tablename__ = "canvas_enrollment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False)
    canvas_course_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    canvas_enrollment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    canvas_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    sync_run = relationship("CanvasSyncRun", back_populates="enrollment_snapshots")


class CanvasSubmissionSnapshot(Base):
    __tablename__ = "canvas_submission_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False)
    canvas_course_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    canvas_assignment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    canvas_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    score: Mapped[Optional[float]] = mapped_column()
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    sync_run = relationship("CanvasSyncRun", back_populates="submission_snapshots")
