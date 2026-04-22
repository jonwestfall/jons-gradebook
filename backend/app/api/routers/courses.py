from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    AssignmentMatchDecision,
    AssignmentMatchSuggestion,
    AssignmentSource,
    ClassSchedule,
    Course,
    CourseGradeRule,
    GradeEntry,
    GradeSource,
    GradeStatus,
    GradeRuleTemplate,
    MatchStatus,
)
from app.db.session import get_db
from app.schemas.academic import (
    AssignmentCreate,
    AssignmentOut,
    AttachRuleRequest,
    ClassScheduleCreate,
    CourseCreate,
    CourseOut,
    GradeEntryUpsert,
    GradeRuleTemplateCreate,
    MatchBulkActionRequest,
    MeetingGenerateRequest,
)
from app.services.attendance import generate_meetings
from app.services.gradebook import build_merged_gradebook
from app.services.matching import confirm_canvas_authoritative, reject_match_suggestion, suggest_matches_for_course

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return db.scalars(select(Course).order_by(Course.name.asc())).all()


@router.post("/", response_model=CourseOut)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)) -> Course:
    course = Course(name=payload.name, section_name=payload.section_name, term_name=payload.term_name)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/{course_id}/assignments/local", response_model=AssignmentOut)
def create_local_assignment(course_id: int, payload: AssignmentCreate, db: Session = Depends(get_db)) -> Assignment:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assignment = Assignment(
        course_id=course_id,
        assignment_group_id=payload.assignment_group_id,
        source=AssignmentSource.local,
        title=payload.title,
        description=payload.description,
        due_at=payload.due_at,
        points_possible=payload.points_possible,
        is_archived=False,
        is_hidden=False,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{course_id}/assignments/{assignment_id}/grades")
def upsert_assignment_grade(
    course_id: int,
    assignment_id: int,
    payload: GradeEntryUpsert,
    db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(Assignment, assignment_id)
    if not assignment or assignment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Assignment not found")

    grade = db.scalar(
        select(GradeEntry).where(
            GradeEntry.assignment_id == assignment_id,
            GradeEntry.student_id == payload.student_id,
        )
    )

    try:
        status = GradeStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid grade status") from exc

    if not grade:
        grade = GradeEntry(
            assignment_id=assignment_id,
            student_id=payload.student_id,
            source=GradeSource.local,
            status=status,
            score=payload.score,
        )
        db.add(grade)
    else:
        grade.source = GradeSource.local
        grade.status = status
        grade.score = payload.score

    db.commit()
    db.refresh(grade)
    return {
        "id": grade.id,
        "assignment_id": grade.assignment_id,
        "student_id": grade.student_id,
        "score": grade.score,
        "status": grade.status.value,
        "source": grade.source.value,
    }


@router.get("/{course_id}/gradebook")
def merged_gradebook(
    course_id: int,
    include_hidden: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return build_merged_gradebook(db, course_id=course_id, include_hidden=include_hidden)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{course_id}/matches/suggest")
def suggest_assignment_matches(course_id: int, db: Session = Depends(get_db)) -> list[dict]:
    suggestions = suggest_matches_for_course(db, course_id)
    return _serialize_match_suggestions(suggestions)


@router.get("/{course_id}/matches")
def list_assignment_matches(
    course_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(AssignmentMatchSuggestion).where(AssignmentMatchSuggestion.course_id == course_id)
    if status:
        try:
            parsed_status = MatchStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid match status") from exc
        query = query.where(AssignmentMatchSuggestion.status == parsed_status)
    suggestions = db.scalars(query.order_by(AssignmentMatchSuggestion.confidence.desc())).all()
    return _serialize_match_suggestions(suggestions)


def _serialize_match_suggestions(suggestions: list[AssignmentMatchSuggestion]) -> list[dict]:
    return [
        {
            "id": suggestion.id,
            "course_id": suggestion.course_id,
            "canvas_assignment_id": suggestion.canvas_assignment_id,
            "canvas_assignment_title": suggestion.canvas_assignment.title if suggestion.canvas_assignment else None,
            "local_assignment_id": suggestion.local_assignment_id,
            "local_assignment_title": suggestion.local_assignment.title if suggestion.local_assignment else None,
            "confidence": suggestion.confidence,
            "name_score": suggestion.name_score,
            "due_date_score": suggestion.due_date_score,
            "points_score": suggestion.points_score,
            "status": suggestion.status.value,
            "rationale": suggestion.rationale,
            "updated_at": suggestion.updated_at.isoformat(),
        }
        for suggestion in suggestions
    ]


@router.post("/matches/{suggestion_id}/confirm-canvas")
def confirm_canvas_match(suggestion_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        suggestion = confirm_canvas_authoritative(db, suggestion_id)
        return {
            "id": suggestion.id,
            "status": suggestion.status.value,
            "local_assignment_archived": suggestion.local_assignment.is_archived,
            "local_assignment_hidden": suggestion.local_assignment.is_hidden,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/matches/{suggestion_id}/reject")
def reject_canvas_match(suggestion_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        suggestion = reject_match_suggestion(db, suggestion_id)
        return {
            "id": suggestion.id,
            "status": suggestion.status.value,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/matches/bulk")
def bulk_match_action(payload: MatchBulkActionRequest, db: Session = Depends(get_db)) -> dict:
    updated = 0
    missing_ids: list[int] = []

    for suggestion_id in payload.suggestion_ids:
        try:
            if payload.action == "confirm_canvas":
                confirm_canvas_authoritative(db, suggestion_id)
            else:
                reject_match_suggestion(db, suggestion_id, note=payload.note)
            updated += 1
        except ValueError:
            missing_ids.append(suggestion_id)

    return {
        "action": payload.action,
        "requested_count": len(payload.suggestion_ids),
        "updated_count": updated,
        "missing_ids": missing_ids,
    }


@router.get("/{course_id}/matches/history")
def list_match_decision_history(course_id: int, db: Session = Depends(get_db)) -> list[dict]:
    decisions = db.scalars(
        select(AssignmentMatchDecision)
        .where(AssignmentMatchDecision.course_id == course_id)
        .order_by(AssignmentMatchDecision.created_at.desc())
        .limit(300)
    ).all()
    return [
        {
            "id": decision.id,
            "suggestion_id": decision.suggestion_id,
            "action": decision.action.value,
            "note": decision.note,
            "created_at": decision.created_at.isoformat(),
            "canvas_assignment_title": decision.suggestion.canvas_assignment.title if decision.suggestion else None,
            "local_assignment_title": decision.suggestion.local_assignment.title if decision.suggestion else None,
        }
        for decision in decisions
    ]


@router.post("/rules/templates")
def create_rule_template(payload: GradeRuleTemplateCreate, db: Session = Depends(get_db)) -> dict:
    template = GradeRuleTemplate(
        name=payload.name,
        rule_type=payload.rule_type,
        description=payload.description,
        config=payload.config,
        is_active=True,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "rule_type": template.rule_type.value,
        "config": template.config,
    }


@router.get("/rules/templates")
def list_rule_templates(db: Session = Depends(get_db)) -> list[dict]:
    templates = db.scalars(select(GradeRuleTemplate).order_by(GradeRuleTemplate.name.asc())).all()
    return [
        {
            "id": template.id,
            "name": template.name,
            "rule_type": template.rule_type.value,
            "description": template.description,
            "config": template.config,
            "is_active": template.is_active,
        }
        for template in templates
    ]


@router.post("/{course_id}/rules")
def attach_rule_to_course(course_id: int, payload: AttachRuleRequest, db: Session = Depends(get_db)) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    template = db.get(GradeRuleTemplate, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Rule template not found")

    link = db.scalar(
        select(CourseGradeRule).where(
            CourseGradeRule.course_id == course_id,
            CourseGradeRule.template_id == payload.template_id,
        )
    )
    if not link:
        link = CourseGradeRule(course_id=course_id, template_id=payload.template_id, is_enabled=payload.is_enabled)
        db.add(link)
    else:
        link.is_enabled = payload.is_enabled

    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "course_id": link.course_id,
        "template_id": link.template_id,
        "is_enabled": link.is_enabled,
    }


@router.post("/meetings/generate")
def generate_course_meetings(payload: MeetingGenerateRequest, db: Session = Depends(get_db)) -> list[dict]:
    meetings = generate_meetings(db, payload.course_id, payload.start_date, payload.end_date)
    return [
        {
            "id": meeting.id,
            "course_id": meeting.course_id,
            "meeting_date": meeting.meeting_date.isoformat(),
            "is_generated": meeting.is_generated,
        }
        for meeting in meetings
    ]


@router.get("/{course_id}/schedules")
def list_course_schedules(course_id: int, db: Session = Depends(get_db)) -> list[dict]:
    schedules = db.scalars(select(ClassSchedule).where(ClassSchedule.course_id == course_id)).all()
    return [
        {
            "id": schedule.id,
            "course_id": schedule.course_id,
            "weekday": schedule.weekday,
            "start_time": schedule.start_time.isoformat(),
            "end_time": schedule.end_time.isoformat(),
            "room": schedule.room,
        }
        for schedule in schedules
    ]


@router.post("/{course_id}/schedules")
def create_course_schedule(course_id: int, payload: ClassScheduleCreate, db: Session = Depends(get_db)) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    schedule = ClassSchedule(course_id=course_id, **payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return {
        "id": schedule.id,
        "course_id": schedule.course_id,
        "weekday": schedule.weekday,
        "start_time": schedule.start_time.isoformat(),
        "end_time": schedule.end_time.isoformat(),
        "room": schedule.room,
    }
