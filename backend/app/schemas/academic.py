from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import (
    AssignmentGradingType,
    AssignmentSource,
    CalculatedColumnOperation,
    CompletionStatus,
    RuleType,
)


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
    grading_type: AssignmentGradingType = AssignmentGradingType.points


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    source: AssignmentSource
    due_at: datetime | None
    points_possible: float | None
    grading_type: AssignmentGradingType
    is_archived: bool
    is_hidden: bool


class GradeEntryUpsert(BaseModel):
    student_id: int
    score: float | None = None
    letter_grade: str | None = None
    completion_status: CompletionStatus | None = None
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
    weekdays: list[int] = Field(default_factory=list)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        normalized = sorted(set(value))
        for weekday in normalized:
            if weekday < 0 or weekday > 6:
                raise ValueError("weekdays must be in range 0..6")
        return normalized


class MatchBulkActionRequest(BaseModel):
    suggestion_ids: list[int] = Field(min_length=1)
    action: Literal["confirm_canvas", "reject"]
    note: str | None = None


class CalculatedColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    operation: CalculatedColumnOperation
    assignment_ids: list[int] = Field(default_factory=list)


class CalculatedColumnUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    operation: CalculatedColumnOperation | None = None
    assignment_ids: list[int] | None = None


class GradebookColumnReorderRequest(BaseModel):
    assignment_order: list[int] = Field(default_factory=list)
    calculated_column_order: list[int] = Field(default_factory=list)


MessageFilterKind = Literal["not_submitted", "not_graded", "score_below", "score_above", "missing"]


class MessageStudentsRequest(BaseModel):
    assignment_id: int
    filter_kind: MessageFilterKind
    threshold: float | None = None
    include_excused: bool = False
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    template_name: str | None = Field(default=None, max_length=120)
    recurrence_days: int | None = Field(default=None, ge=1, le=30)
    create_followup_tasks: bool = False
