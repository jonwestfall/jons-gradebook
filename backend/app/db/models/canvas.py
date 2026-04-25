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


class CanvasSyncEntityType(str, enum.Enum):
    course = "course"
    enrollment = "enrollment"
    assignment = "assignment"
    submission = "submission"


class CanvasSyncEventAction(str, enum.Enum):
    created = "created"
    updated = "updated"
    deleted = "deleted"
    unchanged = "unchanged"


class CanvasSyncConflictStatus(str, enum.Enum):
    pending = "pending"
    kept_local = "kept_local"
    accepted_canvas = "accepted_canvas"
    ignored = "ignored"


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
    events = relationship("CanvasSyncEvent", back_populates="sync_run", cascade="all, delete-orphan")
    conflicts = relationship("CanvasSyncConflict", back_populates="sync_run", cascade="all, delete-orphan")


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


class CanvasStudentFieldMapping(Base, TimestampMixin):
    __tablename__ = "canvas_student_field_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_field: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


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


class CanvasSyncEvent(Base, TimestampMixin):
    __tablename__ = "canvas_sync_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[CanvasSyncEntityType] = mapped_column(Enum(CanvasSyncEntityType), nullable=False)
    action: Mapped[CanvasSyncEventAction] = mapped_column(Enum(CanvasSyncEventAction), nullable=False)
    canvas_course_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    canvas_item_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    local_item_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    sync_run = relationship("CanvasSyncRun", back_populates="events")


class CanvasSyncConflict(Base, TimestampMixin):
    __tablename__ = "canvas_sync_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_run_id: Mapped[int] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    grade_entry_id: Mapped[int] = mapped_column(ForeignKey("grade_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_snapshot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("canvas_submission_snapshots.id", ondelete="SET NULL")
    )
    canvas_course_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    canvas_assignment_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    canvas_user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    local_score: Mapped[Optional[float]] = mapped_column()
    canvas_score: Mapped[Optional[float]] = mapped_column()
    local_status: Mapped[Optional[str]] = mapped_column(String(40))
    canvas_status: Mapped[Optional[str]] = mapped_column(String(40))
    local_source: Mapped[Optional[str]] = mapped_column(String(40))
    status: Mapped[CanvasSyncConflictStatus] = mapped_column(
        Enum(CanvasSyncConflictStatus, native_enum=False),
        nullable=False,
        default=CanvasSyncConflictStatus.pending,
    )
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    sync_run = relationship("CanvasSyncRun", back_populates="conflicts")
    course = relationship("Course")
    assignment = relationship("Assignment")
    student = relationship("StudentProfile")
    grade_entry = relationship("GradeEntry")
    submission_snapshot = relationship("CanvasSubmissionSnapshot")
