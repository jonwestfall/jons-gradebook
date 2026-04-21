from __future__ import annotations

import enum
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class EnrollmentRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    ta = "ta"


class AssignmentSource(str, enum.Enum):
    canvas = "canvas"
    local = "local"


class MatchStatus(str, enum.Enum):
    suggested = "suggested"
    confirmed = "confirmed"
    rejected = "rejected"


class GradeSource(str, enum.Enum):
    canvas = "canvas"
    local = "local"
    manual_override = "manual_override"


class GradeStatus(str, enum.Enum):
    graded = "graded"
    missing = "missing"
    excused = "excused"
    unsubmitted = "unsubmitted"


class RuleType(str, enum.Enum):
    drop_lowest_in_group = "drop_lowest_in_group"
    required_completion_gate = "required_completion_gate"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    tardy = "tardy"
    excused = "excused"


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canvas_course_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_name: Mapped[Optional[str]] = mapped_column(String(255))
    term_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    assignment_groups = relationship("AssignmentGroup", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    grade_rules = relationship("CourseGradeRule", back_populates="course", cascade="all, delete-orphan")
    schedules = relationship("ClassSchedule", back_populates="course", cascade="all, delete-orphan")
    meetings = relationship("ClassMeeting", back_populates="course", cascade="all, delete-orphan")


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canvas_user_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    student_number: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    institution_name: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    grades = relationship("GradeEntry", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_enrollment_course_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[EnrollmentRole] = mapped_column(Enum(EnrollmentRole), nullable=False, default=EnrollmentRole.student)
    canvas_enrollment_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    course = relationship("Course", back_populates="enrollments")
    student = relationship("StudentProfile", back_populates="enrollments")


class AssignmentGroup(Base, TimestampMixin):
    __tablename__ = "assignment_groups"
    __table_args__ = (UniqueConstraint("course_id", "name", name="uq_assignment_group_name_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Float)

    course = relationship("Course", back_populates="assignment_groups")
    assignments = relationship("Assignment", back_populates="assignment_group")


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assignment_groups.id", ondelete="SET NULL"))
    source: Mapped[AssignmentSource] = mapped_column(Enum(AssignmentSource), nullable=False)
    canvas_assignment_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    points_possible: Mapped[Optional[float]] = mapped_column(Float)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hidden_reason: Mapped[Optional[str]] = mapped_column(String(255))

    course = relationship("Course", back_populates="assignments")
    assignment_group = relationship("AssignmentGroup", back_populates="assignments")
    grade_entries = relationship("GradeEntry", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentMatchSuggestion(Base, TimestampMixin):
    __tablename__ = "assignment_match_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "canvas_assignment_id", "local_assignment_id", name="uq_assignment_match_triplet"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    canvas_assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    local_assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    name_score: Mapped[float] = mapped_column(Float, nullable=False)
    due_date_score: Mapped[float] = mapped_column(Float, nullable=False)
    points_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), nullable=False, default=MatchStatus.suggested)
    rationale: Mapped[Optional[str]] = mapped_column(Text)

    course = relationship("Course")
    canvas_assignment = relationship("Assignment", foreign_keys=[canvas_assignment_id])
    local_assignment = relationship("Assignment", foreign_keys=[local_assignment_id])


class GradeEntry(Base, TimestampMixin):
    __tablename__ = "grade_entries"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_grade_assignment_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[GradeSource] = mapped_column(Enum(GradeSource), nullable=False)
    status: Mapped[GradeStatus] = mapped_column(Enum(GradeStatus), nullable=False, default=GradeStatus.unsubmitted)
    score: Mapped[Optional[float]] = mapped_column(Float)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    snapshot_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("canvas_sync_runs.id", ondelete="SET NULL"))

    assignment = relationship("Assignment", back_populates="grade_entries")
    student = relationship("StudentProfile", back_populates="grades")


class GradeRuleTemplate(Base, TimestampMixin):
    __tablename__ = "grade_rule_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course_links = relationship("CourseGradeRule", back_populates="template")


class CourseGradeRule(Base, TimestampMixin):
    __tablename__ = "course_grade_rules"
    __table_args__ = (UniqueConstraint("course_id", "template_id", name="uq_course_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("grade_rule_templates.id", ondelete="CASCADE"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course = relationship("Course", back_populates="grade_rules")
    template = relationship("GradeRuleTemplate", back_populates="course_links")


class ClassSchedule(Base, TimestampMixin):
    __tablename__ = "class_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[Optional[str]] = mapped_column(String(120))

    course = relationship("Course", back_populates="schedules")


class ClassMeeting(Base, TimestampMixin):
    __tablename__ = "class_meetings"
    __table_args__ = (UniqueConstraint("course_id", "meeting_date", name="uq_class_meeting_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    schedule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("class_schedules.id", ondelete="SET NULL"))
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_canceled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    course = relationship("Course", back_populates="meetings")
    attendance_records = relationship("AttendanceRecord", back_populates="meeting", cascade="all, delete-orphan")


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("meeting_id", "student_id", name="uq_attendance_meeting_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("class_meetings.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)

    meeting = relationship("ClassMeeting", back_populates="attendance_records")
    student = relationship("StudentProfile", back_populates="attendance_records")
