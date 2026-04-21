from __future__ import annotations

from datetime import datetime
from typing import Sequence

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    AssignmentMatchSuggestion,
    AssignmentSource,
    MatchStatus,
)


def _date_score(canvas_due: datetime | None, local_due: datetime | None) -> float:
    if not canvas_due or not local_due:
        return 0.5
    days = abs((canvas_due - local_due).days)
    return max(0.0, 1.0 - (days / 14.0))


def _points_score(canvas_points: float | None, local_points: float | None) -> float:
    if canvas_points is None or local_points is None:
        return 0.5
    baseline = max(canvas_points, local_points, 1.0)
    diff = abs(canvas_points - local_points)
    return max(0.0, 1.0 - (diff / baseline))


def _name_score(canvas_name: str, local_name: str) -> float:
    return fuzz.token_set_ratio(canvas_name, local_name) / 100.0


def suggest_matches_for_course(db: Session, course_id: int, threshold: float = 0.55) -> Sequence[AssignmentMatchSuggestion]:
    assignments = db.scalars(select(Assignment).where(Assignment.course_id == course_id)).all()

    canvas_assignments = [a for a in assignments if a.source == AssignmentSource.canvas and not a.is_archived]
    local_assignments = [a for a in assignments if a.source == AssignmentSource.local and not a.is_archived]

    suggestions: list[AssignmentMatchSuggestion] = []

    for canvas_assignment in canvas_assignments:
        for local_assignment in local_assignments:
            name_score = _name_score(canvas_assignment.title, local_assignment.title)
            due_date_score = _date_score(canvas_assignment.due_at, local_assignment.due_at)
            points_score = _points_score(canvas_assignment.points_possible, local_assignment.points_possible)
            confidence = (0.6 * name_score) + (0.25 * due_date_score) + (0.15 * points_score)

            if confidence < threshold:
                continue

            existing = db.scalar(
                select(AssignmentMatchSuggestion).where(
                    AssignmentMatchSuggestion.course_id == course_id,
                    AssignmentMatchSuggestion.canvas_assignment_id == canvas_assignment.id,
                    AssignmentMatchSuggestion.local_assignment_id == local_assignment.id,
                )
            )

            if existing:
                existing.confidence = confidence
                existing.name_score = name_score
                existing.due_date_score = due_date_score
                existing.points_score = points_score
                existing.rationale = (
                    f"Name={name_score:.2f}; DueDate={due_date_score:.2f}; Points={points_score:.2f}"
                )
                suggestions.append(existing)
            else:
                suggestion = AssignmentMatchSuggestion(
                    course_id=course_id,
                    canvas_assignment_id=canvas_assignment.id,
                    local_assignment_id=local_assignment.id,
                    confidence=confidence,
                    name_score=name_score,
                    due_date_score=due_date_score,
                    points_score=points_score,
                    status=MatchStatus.suggested,
                    rationale=f"Name={name_score:.2f}; DueDate={due_date_score:.2f}; Points={points_score:.2f}",
                )
                db.add(suggestion)
                suggestions.append(suggestion)

    db.commit()

    for suggestion in suggestions:
        db.refresh(suggestion)
    return suggestions


def confirm_canvas_authoritative(db: Session, suggestion_id: int) -> AssignmentMatchSuggestion:
    suggestion = db.get(AssignmentMatchSuggestion, suggestion_id)
    if not suggestion:
        raise ValueError("Suggestion not found")

    suggestion.status = MatchStatus.confirmed
    local_assignment = suggestion.local_assignment
    local_assignment.is_archived = True
    local_assignment.is_hidden = True
    local_assignment.hidden_reason = "Canvas authoritative match confirmed"

    db.commit()
    db.refresh(suggestion)
    return suggestion
