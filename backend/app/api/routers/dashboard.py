from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AlertStatus,
    Assignment,
    AssignmentSource,
    AssignmentMatchSuggestion,
    CanvasSyncRun,
    GradeEntry,
    GradeSource,
    MatchStatus,
    StudentAlert,
    Task,
    TaskStatus,
)
from app.db.session import get_db
from app.services.risk import compute_risk_for_students

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)

    out_of_sync_overrides = db.scalar(
        select(func.count(GradeEntry.id))
        .join(Assignment, GradeEntry.assignment_id == Assignment.id)
        .where(
            Assignment.source == AssignmentSource.canvas,
            GradeEntry.source.in_([GradeSource.local, GradeSource.manual_override]),
        )
    ) or 0

    unread_alerts = db.scalar(
        select(func.count(StudentAlert.id)).where(StudentAlert.status == AlertStatus.active)
    ) or 0

    upcoming_followups = db.scalar(
        select(func.count(Task.id)).where(
            Task.status.in_([TaskStatus.open, TaskStatus.in_progress]),
            Task.due_at.is_not(None),
            Task.due_at <= now + timedelta(days=7),
        )
    ) or 0

    open_match_suggestions = db.scalar(
        select(func.count(AssignmentMatchSuggestion.id)).where(AssignmentMatchSuggestion.status == MatchStatus.suggested)
    ) or 0

    latest_sync = db.scalar(select(CanvasSyncRun).order_by(CanvasSyncRun.started_at.desc()).limit(1))

    risk_rows = compute_risk_for_students(db)
    top_risk = [
        {
            "student_id": row.student_id,
            "student_name": row.student_name,
            "risk_score": row.risk_score,
            "level": row.level,
            "missing_assignments": row.missing_assignments,
            "current_percent": row.current_percent,
            "days_since_interaction": row.days_since_interaction,
            "reasons": row.reasons,
        }
        for row in risk_rows[:8]
    ]

    return {
        "cards": {
            "needs_grading": int(open_match_suggestions),  # MVP signal: unresolved match/grade cleanup queue
            "missing_late_followup": int(sum(1 for row in risk_rows if row.level in {"medium", "high"})),
            "out_of_sync_overrides": int(out_of_sync_overrides),
            "unread_alerts": int(unread_alerts),
            "upcoming_advising_followups": int(upcoming_followups),
        },
        "top_risk_students": top_risk,
        "latest_sync": {
            "id": latest_sync.id,
            "status": latest_sync.status.value,
            "started_at": latest_sync.started_at.isoformat(),
            "finished_at": latest_sync.finished_at.isoformat() if latest_sync.finished_at else None,
        }
        if latest_sync
        else None,
    }
