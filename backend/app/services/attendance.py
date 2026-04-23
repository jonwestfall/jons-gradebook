from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, AttendanceStatus, ClassMeeting, ClassSchedule


def generate_meetings(db: Session, course_id: int, start_date: date, end_date: date) -> list[ClassMeeting]:
    schedules = db.scalars(select(ClassSchedule).where(ClassSchedule.course_id == course_id)).all()
    if not schedules:
        return []

    schedule_by_weekday = {schedule.weekday: schedule for schedule in schedules}

    meetings: list[ClassMeeting] = []
    cursor = start_date
    while cursor <= end_date:
        schedule = schedule_by_weekday.get(cursor.weekday())
        if schedule:
            existing = db.scalar(
                select(ClassMeeting).where(ClassMeeting.course_id == course_id, ClassMeeting.meeting_date == cursor)
            )
            if not existing:
                meeting = ClassMeeting(
                    course_id=course_id,
                    schedule_id=schedule.id,
                    meeting_date=cursor,
                    is_generated=True,
                )
                db.add(meeting)
                meetings.append(meeting)
        cursor += timedelta(days=1)

    db.commit()
    for meeting in meetings:
        db.refresh(meeting)
    return meetings


def upsert_attendance(
    db: Session,
    meeting_id: int,
    student_id: int,
    status: AttendanceStatus,
    note: str | None = None,
    auto_commit: bool = True,
) -> AttendanceRecord:
    record = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.meeting_id == meeting_id,
            AttendanceRecord.student_id == student_id,
        )
    )
    if not record:
        record = AttendanceRecord(
            meeting_id=meeting_id,
            student_id=student_id,
            status=status,
            note=note,
        )
        db.add(record)
    else:
        record.status = status
        record.note = note

    if auto_commit:
        db.commit()
        db.refresh(record)
    else:
        db.flush()
    return record
