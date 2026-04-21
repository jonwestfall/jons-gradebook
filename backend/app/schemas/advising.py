from datetime import datetime

from pydantic import BaseModel

from app.db.models import MeetingMode


class AdviseeCreate(BaseModel):
    student_profile_id: int | None = None
    first_name: str
    last_name: str
    email: str | None = None
    external_id: str | None = None
    notes: str | None = None


class AdvisingMeetingCreate(BaseModel):
    advisee_id: int
    meeting_at: datetime
    mode: MeetingMode = MeetingMode.in_person
    summary: str | None = None
    action_items: str | None = None
