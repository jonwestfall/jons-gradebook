from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    AssignmentGradingType,
    AttendanceRecord,
    AttendanceStatus,
    GradeEntry,
    GradeStatus,
    InteractionLog,
    StudentProfile,
)


@dataclass
class StudentRisk:
    student_id: int
    student_name: str
    risk_score: int
    level: str
    missing_assignments: int
    attendance_absence_rate: float | None
    current_percent: float | None
    days_since_interaction: int | None
    reasons: list[str]


def _safe_percent(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def compute_student_risk(
    db: Session,
    student_id: int,
    low_grade_threshold: float = 70.0,
    missing_threshold: int = 2,
    stale_interaction_days: int = 14,
) -> StudentRisk:
    student = db.get(StudentProfile, student_id)
    if not student:
        raise ValueError("Student not found")

    now = datetime.now(timezone.utc)
    due_now = now

    # Missing assignments: due passed and unsubmitted/missing.
    missing_rows = db.execute(
        select(GradeEntry, Assignment)
        .join(Assignment, GradeEntry.assignment_id == Assignment.id)
        .where(
            GradeEntry.student_id == student_id,
            Assignment.due_at.is_not(None),
            Assignment.due_at <= due_now,
            GradeEntry.status.in_([GradeStatus.unsubmitted, GradeStatus.missing]),
            Assignment.is_archived.is_(False),
        )
    ).all()
    missing_assignments = len(missing_rows)

    # Current percent across points-based assignments.
    grade_rows = db.execute(
        select(GradeEntry, Assignment)
        .join(Assignment, GradeEntry.assignment_id == Assignment.id)
        .where(
            GradeEntry.student_id == student_id,
            Assignment.is_archived.is_(False),
            Assignment.grading_type == AssignmentGradingType.points,
        )
    ).all()
    possible = 0.0
    earned = 0.0
    for grade, assignment in grade_rows:
        if assignment.points_possible:
            possible += float(assignment.points_possible)
            if grade.score is not None:
                earned += float(grade.score)
    current_percent = _safe_percent(earned, possible)

    # Attendance absence rate.
    attendance_rows = db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id == student_id)).all()
    absent_like = sum(1 for row in attendance_rows if row.status in {AttendanceStatus.absent, AttendanceStatus.tardy})
    attendance_absence_rate = _safe_percent(absent_like, len(attendance_rows))

    latest_interaction_at = db.scalar(
        select(func.max(InteractionLog.occurred_at)).where(InteractionLog.student_profile_id == student_id)
    )
    days_since_interaction = None
    if latest_interaction_at:
        if latest_interaction_at.tzinfo is None:
            latest_interaction_at = latest_interaction_at.replace(tzinfo=timezone.utc)
        days_since_interaction = max(0, (now - latest_interaction_at).days)

    score = 0
    reasons: list[str] = []

    if missing_assignments >= missing_threshold:
        score += 35
        reasons.append(f"{missing_assignments} missing assignments")
    elif missing_assignments > 0:
        score += 15
        reasons.append(f"{missing_assignments} missing assignment")

    if current_percent is not None and current_percent < low_grade_threshold:
        score += 30
        reasons.append(f"current grade below {low_grade_threshold:.0f}%")

    if attendance_absence_rate is not None and attendance_absence_rate >= 25:
        score += 20
        reasons.append("attendance risk (absent/tardy >= 25%)")

    if days_since_interaction is not None and days_since_interaction >= stale_interaction_days:
        score += 15
        reasons.append(f"no interaction in {days_since_interaction} days")

    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    return StudentRisk(
        student_id=student.id,
        student_name=f"{student.first_name} {student.last_name}".strip(),
        risk_score=score,
        level=level,
        missing_assignments=missing_assignments,
        attendance_absence_rate=attendance_absence_rate,
        current_percent=current_percent,
        days_since_interaction=days_since_interaction,
        reasons=reasons,
    )


def compute_risk_for_students(
    db: Session,
    student_ids: Iterable[int] | None = None,
    *,
    low_grade_threshold: float = 70.0,
    missing_threshold: int = 2,
    stale_interaction_days: int = 14,
) -> list[StudentRisk]:
    if student_ids is None:
        student_ids = db.scalars(select(StudentProfile.id)).all()
    results: list[StudentRisk] = []
    for student_id in student_ids:
        try:
            risk = compute_student_risk(
                db,
                student_id=student_id,
                low_grade_threshold=low_grade_threshold,
                missing_threshold=missing_threshold,
                stale_interaction_days=stale_interaction_days,
            )
            results.append(risk)
        except ValueError:
            continue
    results.sort(key=lambda item: item.risk_score, reverse=True)
    return results


def should_trigger_intervention(risk: StudentRisk, min_score: int = 60) -> bool:
    return risk.risk_score >= min_score
