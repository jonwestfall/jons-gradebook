from __future__ import annotations

from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.db.models import Advisee, Course, Enrollment, InteractionLog, InteractionType, StudentProfile
from app.db.session import get_db
from app.schemas.interactions import InteractionBulkCreate, InteractionCreate

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/")
def list_interactions(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    interaction_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="occurred_at"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(InteractionLog)

    if start_date is not None:
        query = query.where(InteractionLog.occurred_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
    if end_date is not None:
        query = query.where(InteractionLog.occurred_at <= datetime.combine(end_date, time.max, tzinfo=timezone.utc))

    if interaction_type:
        try:
            parsed_type = InteractionType(interaction_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid interaction_type") from exc
        query = query.where(InteractionLog.interaction_type == parsed_type)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(InteractionLog.summary.ilike(pattern), InteractionLog.notes.ilike(pattern)))

    sort_field_map = {
        "occurred_at": InteractionLog.occurred_at,
        "interaction_type": InteractionLog.interaction_type,
        "summary": InteractionLog.summary,
        "id": InteractionLog.id,
    }
    sort_field = sort_field_map.get(sort_by, InteractionLog.occurred_at)
    direction = asc if sort_order.lower() == "asc" else desc
    query = query.order_by(direction(sort_field), direction(InteractionLog.id)).limit(limit)

    interactions = db.scalars(query).all()

    student_ids = {interaction.student_profile_id for interaction in interactions if interaction.student_profile_id is not None}
    advisee_ids = {interaction.advisee_id for interaction in interactions if interaction.advisee_id is not None}

    students = (
        db.scalars(select(StudentProfile).where(StudentProfile.id.in_(student_ids))).all() if student_ids else []
    )
    advisees = db.scalars(select(Advisee).where(Advisee.id.in_(advisee_ids))).all() if advisee_ids else []

    student_map = {student.id: f"{student.first_name} {student.last_name}".strip() for student in students}
    advisee_map = {advisee.id: f"{advisee.first_name} {advisee.last_name}".strip() for advisee in advisees}

    return [
        {
            "id": interaction.id,
            "student_profile_id": interaction.student_profile_id,
            "advisee_id": interaction.advisee_id,
            "student_name": student_map.get(interaction.student_profile_id),
            "advisee_name": advisee_map.get(interaction.advisee_id),
            "interaction_type": interaction.interaction_type.value,
            "occurred_at": interaction.occurred_at.isoformat(),
            "summary": interaction.summary,
            "notes": interaction.notes,
            "metadata": interaction.metadata_json,
        }
        for interaction in interactions
    ]


@router.post("/")
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)) -> dict:
    interaction = InteractionLog(**payload.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return {
        "id": interaction.id,
        "interaction_type": interaction.interaction_type.value,
        "occurred_at": interaction.occurred_at.isoformat(),
    }


@router.get("/targets")
def list_interaction_targets(db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    courses = db.scalars(select(Course).order_by(Course.name.asc())).all()
    advisees = db.scalars(select(Advisee).order_by(Advisee.last_name.asc(), Advisee.first_name.asc())).all()

    enrollment_counts = {}
    if courses:
        course_ids = [course.id for course in courses]
        enrollments = db.scalars(select(Enrollment).where(Enrollment.course_id.in_(course_ids))).all()
        for enrollment in enrollments:
            enrollment_counts[enrollment.course_id] = enrollment_counts.get(enrollment.course_id, 0) + 1

    return {
        "students": [
            {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "email": student.email,
            }
            for student in students
        ],
        "courses": [
            {
                "id": course.id,
                "name": course.name,
                "section_name": course.section_name,
                "student_count": enrollment_counts.get(course.id, 0),
            }
            for course in courses
        ],
        "advisees": [
            {
                "id": advisee.id,
                "name": f"{advisee.first_name} {advisee.last_name}".strip(),
                "student_profile_id": advisee.student_profile_id,
            }
            for advisee in advisees
        ],
    }


@router.post("/bulk")
def create_interaction_bulk(payload: InteractionBulkCreate, db: Session = Depends(get_db)) -> dict:
    created = 0

    if payload.target_scope == "student":
        if payload.target_id is None:
            raise HTTPException(status_code=400, detail="target_id is required for student scope")
        student = db.get(StudentProfile, payload.target_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        db.add(
            InteractionLog(
                student_profile_id=student.id,
                advisee_id=None,
                interaction_type=payload.interaction_type,
                occurred_at=payload.occurred_at,
                summary=payload.summary,
                notes=payload.notes,
                metadata_json={**payload.metadata_json, "target_scope": "student"},
            )
        )
        created = 1

    elif payload.target_scope == "course":
        if payload.target_id is None:
            raise HTTPException(status_code=400, detail="target_id is required for course scope")
        course = db.get(Course, payload.target_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        enrollments = db.scalars(select(Enrollment).where(Enrollment.course_id == course.id)).all()
        for enrollment in enrollments:
            db.add(
                InteractionLog(
                    student_profile_id=enrollment.student_id,
                    advisee_id=None,
                    interaction_type=payload.interaction_type,
                    occurred_at=payload.occurred_at,
                    summary=payload.summary,
                    notes=payload.notes,
                    metadata_json={
                        **payload.metadata_json,
                        "target_scope": "course",
                        "course_id": course.id,
                        "course_name": course.name,
                    },
                )
            )
            created += 1

    elif payload.target_scope == "advisees":
        advisees = db.scalars(select(Advisee)).all()
        for advisee in advisees:
            db.add(
                InteractionLog(
                    student_profile_id=advisee.student_profile_id,
                    advisee_id=advisee.id,
                    interaction_type=payload.interaction_type,
                    occurred_at=payload.occurred_at,
                    summary=payload.summary,
                    notes=payload.notes,
                    metadata_json={**payload.metadata_json, "target_scope": "advisees"},
                )
            )
            created += 1
    else:
        raise HTTPException(status_code=400, detail="Unsupported target_scope")

    db.commit()
    return {"created_count": created, "target_scope": payload.target_scope}
