from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import AdvisingMeeting, Enrollment, InteractionLog, StudentProfile
from app.db.session import get_db

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/")
def list_students(db: Session = Depends(get_db)) -> list[dict]:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    return [
        {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
            "student_number": student.student_number,
            "canvas_user_id": student.canvas_user_id,
        }
        for student in students
    ]


@router.get("/{student_id}/profile")
def student_profile(student_id: int, db: Session = Depends(get_db)) -> dict:
    student = db.scalar(
        select(StudentProfile)
        .where(StudentProfile.id == student_id)
        .options(joinedload(StudentProfile.enrollments).joinedload(Enrollment.course))
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    interactions = db.scalars(
        select(InteractionLog)
        .where(InteractionLog.student_profile_id == student_id)
        .order_by(InteractionLog.occurred_at.desc())
        .limit(15)
    ).all()

    advising_meetings = db.scalars(
        select(AdvisingMeeting)
        .join(AdvisingMeeting.advisee)
        .where(AdvisingMeeting.advisee.has(student_profile_id=student_id))
        .order_by(AdvisingMeeting.meeting_at.desc())
    ).all()

    return {
        "student": {
            "id": student.id,
            "name": f"{student.first_name} {student.last_name}",
            "email": student.email,
            "student_number": student.student_number,
            "institution_name": student.institution_name,
        },
        "courses": [
            {
                "course_id": enrollment.course.id,
                "name": enrollment.course.name,
                "section_name": enrollment.course.section_name,
            }
            for enrollment in student.enrollments
        ],
        "recent_interactions": [
            {
                "id": interaction.id,
                "type": interaction.interaction_type.value,
                "occurred_at": interaction.occurred_at.isoformat(),
                "summary": interaction.summary,
            }
            for interaction in interactions
        ],
        "advising_meetings": [
            {
                "id": meeting.id,
                "meeting_at": meeting.meeting_at.isoformat(),
                "mode": meeting.mode.value,
                "summary": meeting.summary,
                "action_items": meeting.action_items,
            }
            for meeting in advising_meetings
        ],
    }
