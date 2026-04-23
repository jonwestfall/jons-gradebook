from __future__ import annotations

from collections import defaultdict
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.db.models import (
    AttendanceRecord,
    AttendanceStatus,
    ClassMeeting,
    Course,
    Enrollment,
    EnrollmentRole,
    InteractionLog,
    InteractionType,
    StudentProfile,
)
from app.db.session import get_db
from app.schemas.attendance import AttendanceSettingsUpdateRequest, AttendanceUpsertRequest, ManualMeetingCreateRequest
from app.services.attendance import upsert_attendance

router = APIRouter(prefix="/attendance", tags=["attendance"])
DEFAULT_LATE_WEIGHT = 0.8
logger = logging.getLogger(__name__)


@router.get("/courses")
def list_attendance_courses(db: Session = Depends(get_db)) -> list[dict]:
    courses = db.scalars(select(Course).order_by(Course.name.asc())).all()
    return [
        {
            "id": course.id,
            "name": course.name,
            "section_name": course.section_name,
            "term_name": course.term_name,
        }
        for course in courses
    ]


@router.get("/meetings/{course_id}")
def list_course_meetings(course_id: int, db: Session = Depends(get_db)) -> list[dict]:
    meetings = db.scalars(
        select(ClassMeeting).where(ClassMeeting.course_id == course_id).order_by(ClassMeeting.meeting_date.asc())
    ).all()
    return [
        {
            "id": meeting.id,
            "meeting_date": meeting.meeting_date.isoformat(),
            "is_generated": meeting.is_generated,
            "is_canceled": meeting.is_canceled,
        }
        for meeting in meetings
    ]


@router.get("/rollcall/{course_id}")
def roll_call_view(course_id: int, meeting_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    meetings = db.scalars(
        select(ClassMeeting).where(ClassMeeting.course_id == course_id).order_by(ClassMeeting.meeting_date.asc())
    ).all()
    active_meeting = None
    if meeting_id is not None:
        active_meeting = next((meeting for meeting in meetings if meeting.id == meeting_id), None)
        if not active_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found for this course")
    elif meetings:
        active_meeting = meetings[-1]

    enrollments = db.scalars(
        select(Enrollment)
        .where(Enrollment.course_id == course_id, Enrollment.role == EnrollmentRole.student)
        .order_by(Enrollment.student_id.asc())
    ).all()
    student_ids = [enrollment.student_id for enrollment in enrollments]
    students = (
        db.scalars(select(StudentProfile).where(StudentProfile.id.in_(student_ids)).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
        if student_ids
        else []
    )
    students_by_id = {student.id: student for student in students}

    all_meeting_ids = [meeting.id for meeting in meetings if not meeting.is_canceled]
    all_records = (
        db.scalars(select(AttendanceRecord).where(AttendanceRecord.meeting_id.in_(all_meeting_ids))).all()
        if all_meeting_ids
        else []
    )
    by_meeting_student = {(record.meeting_id, record.student_id): record for record in all_records}
    late_weight = course.attendance_lateness_weight if course.attendance_lateness_weight is not None else DEFAULT_LATE_WEIGHT
    counts_by_student: dict[int, dict[str, int]] = defaultdict(
        lambda: {"present": 0, "absent": 0, "tardy": 0, "excused": 0, "unmarked": 0}
    )

    for enrollment in enrollments:
        for meeting in meetings:
            if meeting.is_canceled:
                continue
            record = by_meeting_student.get((meeting.id, enrollment.student_id))
            if not record:
                counts_by_student[enrollment.student_id]["unmarked"] += 1
                continue
            counts_by_student[enrollment.student_id][record.status.value] += 1

    students_payload = []
    for enrollment in enrollments:
        student = students_by_id.get(enrollment.student_id)
        if not student:
            continue
        active_record = by_meeting_student.get((active_meeting.id, student.id)) if active_meeting else None
        counts = counts_by_student[student.id]
        total_marked = counts["present"] + counts["absent"] + counts["tardy"] + counts["excused"]
        weighted_total = counts["present"] + (counts["tardy"] * late_weight)
        attendance_percent = round((weighted_total / total_marked) * 100.0, 2) if total_marked > 0 else None
        students_payload.append(
            {
                "student_id": student.id,
                "name": f"{student.last_name}, {student.first_name}",
                "email": student.email,
                "status": active_record.status.value if active_record else "unmarked",
                "note": active_record.note if active_record else None,
                "counts": counts,
                "attendance_percent": attendance_percent,
            }
        )

    return {
        "course": {
            "id": course.id,
            "name": course.name,
            "section_name": course.section_name,
            "term_name": course.term_name,
            "attendance_lateness_weight": course.attendance_lateness_weight,
            "attendance_excluded_from_final_grade": course.attendance_excluded_from_final_grade,
        },
        "lateness_weight": late_weight,
        "meetings": [
            {
                "id": meeting.id,
                "meeting_date": meeting.meeting_date.isoformat(),
                "is_generated": meeting.is_generated,
                "is_canceled": meeting.is_canceled,
            }
            for meeting in meetings
        ],
        "active_meeting_id": active_meeting.id if active_meeting else None,
        "students": students_payload,
    }


@router.put("/courses/{course_id}/settings")
def update_attendance_settings(course_id: int, payload: AttendanceSettingsUpdateRequest, db: Session = Depends(get_db)) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if payload.lateness_weight < 0 or payload.lateness_weight > 1:
        raise HTTPException(status_code=400, detail="lateness_weight must be between 0 and 1")

    course.attendance_lateness_weight = payload.lateness_weight
    course.attendance_excluded_from_final_grade = payload.excluded_from_final_grade
    db.commit()
    return {
        "course_id": course.id,
        "lateness_weight": course.attendance_lateness_weight,
        "excluded_from_final_grade": course.attendance_excluded_from_final_grade,
    }


@router.post("/meetings")
def create_manual_meeting(payload: ManualMeetingCreateRequest, db: Session = Depends(get_db)) -> dict:
    existing = db.scalar(
        select(ClassMeeting).where(
            ClassMeeting.course_id == payload.course_id,
            ClassMeeting.meeting_date == payload.meeting_date,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Meeting already exists for this date")

    meeting = ClassMeeting(
        course_id=payload.course_id,
        schedule_id=payload.schedule_id,
        meeting_date=payload.meeting_date,
        is_generated=False,
        is_canceled=False,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return {
        "id": meeting.id,
        "course_id": meeting.course_id,
        "meeting_date": meeting.meeting_date.isoformat(),
        "is_generated": meeting.is_generated,
    }


@router.delete("/meetings/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    meeting = db.get(ClassMeeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.delete(meeting)
    db.commit()
    return {"deleted": True, "meeting_id": meeting_id}


@router.post("/meetings/{meeting_id}/mark-all-present")
def mark_all_present(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    meeting = db.get(ClassMeeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    enrollments = db.scalars(
        select(Enrollment).where(Enrollment.course_id == meeting.course_id, Enrollment.role == EnrollmentRole.student)
    ).all()
    updated = 0
    for enrollment in enrollments:
        upsert_attendance(
            db,
            meeting_id=meeting_id,
            student_id=enrollment.student_id,
            status=AttendanceStatus.present,
            note=None,
            auto_commit=False,
        )
        updated += 1
    db.commit()
    return {"updated": updated, "meeting_id": meeting_id}


@router.post("/meetings/{meeting_id}/unmark-all")
def unmark_all(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    meeting = db.get(ClassMeeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.meeting_id == meeting_id)).all()
    removed = 0
    for record in records:
        db.delete(record)
        removed += 1
    db.commit()
    return {"removed": removed, "meeting_id": meeting_id}


@router.post("/records")
def write_attendance(payload: AttendanceUpsertRequest, db: Session = Depends(get_db)) -> dict:
    meeting = db.get(ClassMeeting, payload.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    record = upsert_attendance(
        db,
        meeting_id=payload.meeting_id,
        student_id=payload.student_id,
        status=payload.status,
        note=payload.note,
        auto_commit=True,
    )

    try:
        interaction = InteractionLog(
            student_profile_id=payload.student_id,
            advisee_id=None,
            interaction_type=InteractionType.attendance,
            occurred_at=datetime.now(timezone.utc),
            summary=f"Attendance marked {payload.status.value} for meeting {payload.meeting_id}",
            notes=payload.note,
            metadata_json={
                "meeting_id": payload.meeting_id,
                "attendance_record_id": record.id,
                "status": payload.status.value,
            },
        )
        db.add(interaction)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist attendance interaction log", extra={"meeting_id": payload.meeting_id, "student_id": payload.student_id})

    return {
        "id": record.id,
        "meeting_id": record.meeting_id,
        "student_id": record.student_id,
        "status": record.status.value,
        "note": record.note,
    }


@router.get("/records/{meeting_id}")
def list_attendance_for_meeting(meeting_id: int, db: Session = Depends(get_db)) -> list[dict]:
    meeting = db.get(ClassMeeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.meeting_id == meeting_id)).all()
    return [
        {
            "id": record.id,
            "student_id": record.student_id,
            "status": record.status.value,
            "note": record.note,
        }
        for record in records
    ]


@router.delete("/records/{meeting_id}/{student_id}")
def clear_attendance_for_student(meeting_id: int, student_id: int, db: Session = Depends(get_db)) -> dict:
    record = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.meeting_id == meeting_id,
            AttendanceRecord.student_id == student_id,
        )
    )
    if not record:
        return {"deleted": False, "meeting_id": meeting_id, "student_id": student_id}

    db.delete(record)
    db.commit()
    return {"deleted": True, "meeting_id": meeting_id, "student_id": student_id}
