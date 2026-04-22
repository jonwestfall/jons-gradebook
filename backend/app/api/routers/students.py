from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    AdvisingMeeting,
    AlertStatus,
    Assignment,
    Enrollment,
    GradeEntry,
    InteractionLog,
    StudentAlert,
    StudentProfile,
    StudentProfileTag,
    StudentTag,
)
from app.db.session import get_db
from app.schemas.students import StudentAlertCreate, StudentAlertUpdate, StudentNotesUpdate, StudentTagCreate

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

    alerts = db.scalars(
        select(StudentAlert)
        .where(StudentAlert.student_id == student_id)
        .order_by(StudentAlert.is_pinned.desc(), StudentAlert.created_at.desc())
    ).all()

    tag_links = db.scalars(
        select(StudentProfileTag)
        .where(StudentProfileTag.student_id == student_id)
        .options(joinedload(StudentProfileTag.tag))
    ).all()

    attendance_counts = Counter(record.status.value for record in student.attendance_records)

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

    grade_rows = db.execute(
        select(GradeEntry, Assignment)
        .join(Assignment, GradeEntry.assignment_id == Assignment.id)
        .where(GradeEntry.student_id == student_id)
    ).all()
    course_totals: dict[int, dict[str, float | str | int]] = {}
    for grade, assignment in grade_rows:
        if assignment.course_id not in course_totals:
            course_totals[assignment.course_id] = {
                "course_id": assignment.course_id,
                "course_name": next(
                    (enrollment.course.name for enrollment in student.enrollments if enrollment.course_id == assignment.course_id),
                    f"Course {assignment.course_id}",
                ),
                "earned": 0.0,
                "possible": 0.0,
            }

        if assignment.points_possible is not None:
            course_totals[assignment.course_id]["possible"] += float(assignment.points_possible)
            if grade.score is not None:
                course_totals[assignment.course_id]["earned"] += float(grade.score)

    grade_overview = []
    for totals in course_totals.values():
        possible = float(totals["possible"])
        earned = float(totals["earned"])
        percent = (earned / possible * 100.0) if possible > 0 else None
        grade_overview.append(
            {
                "course_id": totals["course_id"],
                "course_name": totals["course_name"],
                "earned": round(earned, 2),
                "possible": round(possible, 2),
                "percent": round(percent, 2) if percent is not None else None,
            }
        )
    grade_overview.sort(key=lambda row: (row["percent"] if row["percent"] is not None else 10_000))

    return {
        "student": {
            "id": student.id,
            "name": f"{student.first_name} {student.last_name}",
            "email": student.email,
            "student_number": student.student_number,
            "institution_name": student.institution_name,
            "notes": student.notes,
        },
        "priority_sections": ["alerts", "attendance_summary", "recent_interactions", "grade_overview"],
        "alerts": [
            {
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "is_pinned": alert.is_pinned,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ],
        "flags_tags": [{"id": link.tag.id, "name": link.tag.name} for link in tag_links if link.tag],
        "attendance_summary": {
            "present": attendance_counts.get("present", 0),
            "absent": attendance_counts.get("absent", 0),
            "tardy": attendance_counts.get("tardy", 0),
            "excused": attendance_counts.get("excused", 0),
            "total_records": sum(attendance_counts.values()),
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
        "grade_overview": grade_overview,
    }


@router.patch("/{student_id}/notes")
def update_student_notes(student_id: int, payload: StudentNotesUpdate, db: Session = Depends(get_db)) -> dict:
    student = db.get(StudentProfile, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.notes = payload.notes
    db.commit()
    db.refresh(student)
    return {"student_id": student.id, "notes": student.notes}


@router.post("/{student_id}/alerts")
def create_student_alert(student_id: int, payload: StudentAlertCreate, db: Session = Depends(get_db)) -> dict:
    student = db.get(StudentProfile, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    alert = StudentAlert(
        student_id=student_id,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        status=AlertStatus.active,
        is_pinned=payload.is_pinned,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {
        "id": alert.id,
        "student_id": alert.student_id,
        "title": alert.title,
        "message": alert.message,
        "severity": alert.severity.value,
        "status": alert.status.value,
        "is_pinned": alert.is_pinned,
    }


@router.patch("/{student_id}/alerts/{alert_id}")
def update_student_alert(student_id: int, alert_id: int, payload: StudentAlertUpdate, db: Session = Depends(get_db)) -> dict:
    alert = db.get(StudentAlert, alert_id)
    if not alert or alert.student_id != student_id:
        raise HTTPException(status_code=404, detail="Alert not found")

    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(alert, key, value)

    db.commit()
    db.refresh(alert)
    return {
        "id": alert.id,
        "title": alert.title,
        "message": alert.message,
        "severity": alert.severity.value,
        "status": alert.status.value,
        "is_pinned": alert.is_pinned,
    }


@router.delete("/{student_id}/alerts/{alert_id}")
def delete_student_alert(student_id: int, alert_id: int, db: Session = Depends(get_db)) -> dict:
    alert = db.get(StudentAlert, alert_id)
    if not alert or alert.student_id != student_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"deleted": True, "alert_id": alert_id}


@router.post("/{student_id}/tags")
def add_student_tag(student_id: int, payload: StudentTagCreate, db: Session = Depends(get_db)) -> dict:
    student = db.get(StudentProfile, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    tag_name = payload.name.strip()
    if not tag_name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")

    tag = db.scalar(select(StudentTag).where(StudentTag.name.ilike(tag_name)))
    if not tag:
        tag = StudentTag(name=tag_name)
        db.add(tag)
        db.flush()

    existing_link = db.scalar(
        select(StudentProfileTag).where(StudentProfileTag.student_id == student_id, StudentProfileTag.tag_id == tag.id)
    )
    if not existing_link:
        db.add(StudentProfileTag(student_id=student_id, tag_id=tag.id))
        db.commit()
    else:
        db.commit()

    return {"student_id": student_id, "tag_id": tag.id, "name": tag.name}


@router.delete("/{student_id}/tags/{tag_id}")
def remove_student_tag(student_id: int, tag_id: int, db: Session = Depends(get_db)) -> dict:
    link = db.scalar(
        select(StudentProfileTag).where(StudentProfileTag.student_id == student_id, StudentProfileTag.tag_id == tag_id)
    )
    if not link:
        raise HTTPException(status_code=404, detail="Tag link not found")
    db.delete(link)
    db.commit()
    return {"deleted": True, "student_id": student_id, "tag_id": tag_id}
