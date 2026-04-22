from pydantic import BaseModel, Field

from app.db.models import AlertSeverity, AlertStatus


class StudentAlertCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    severity: AlertSeverity = AlertSeverity.medium
    is_pinned: bool = False


class StudentAlertUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    message: str | None = None
    severity: AlertSeverity | None = None
    status: AlertStatus | None = None
    is_pinned: bool | None = None


class StudentTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class StudentNotesUpdate(BaseModel):
    notes: str | None = None


class StudentProfileUpdate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=32)
