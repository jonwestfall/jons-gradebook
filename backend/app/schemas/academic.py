from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import AssignmentSource, RuleType


class CourseCreate(BaseModel):
    name: str
    section_name: str | None = None
    term_name: str | None = None


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    section_name: str | None
    term_name: str | None
    canvas_course_id: str | None


class AssignmentCreate(BaseModel):
    assignment_group_id: int | None = None
    title: str
    description: str | None = None
    due_at: datetime | None = None
    points_possible: float | None = None
    source: AssignmentSource = AssignmentSource.local


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    source: AssignmentSource
    due_at: datetime | None
    points_possible: float | None
    is_archived: bool
    is_hidden: bool


class GradeEntryUpsert(BaseModel):
    student_id: int
    score: float | None = None
    status: str = Field(default="graded")


class GradeRuleTemplateCreate(BaseModel):
    name: str
    rule_type: RuleType
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class AttachRuleRequest(BaseModel):
    template_id: int
    is_enabled: bool = True


class ClassScheduleCreate(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    room: str | None = None


class MeetingGenerateRequest(BaseModel):
    course_id: int
    start_date: date
    end_date: date
