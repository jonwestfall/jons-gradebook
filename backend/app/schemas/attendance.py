from datetime import date

from pydantic import BaseModel

from app.db.models import AttendanceStatus


class AttendanceUpsertRequest(BaseModel):
    meeting_id: int
    student_id: int
    status: AttendanceStatus
    note: str | None = None


class ManualMeetingCreateRequest(BaseModel):
    course_id: int
    meeting_date: date
    schedule_id: int | None = None


class AttendanceSettingsUpdateRequest(BaseModel):
    lateness_weight: float
    excluded_from_final_grade: bool
