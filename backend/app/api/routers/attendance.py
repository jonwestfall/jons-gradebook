from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.db.models import AttendanceRecord, ClassMeeting, InteractionLog, InteractionType
from app.db.session import get_db
from app.schemas.attendance import AttendanceUpsertRequest, ManualMeetingCreateRequest
from app.services.attendance import upsert_attendance

router = APIRouter(prefix="/attendance", tags=["attendance"])


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
    )

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
