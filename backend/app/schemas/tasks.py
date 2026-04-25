from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    status: TaskStatus = TaskStatus.open
    priority: TaskPriority = TaskPriority.medium
    due_at: datetime | None = None
    note: str | None = None
    linked_student_id: int | None = None
    linked_course_id: int | None = None
    linked_interaction_id: int | None = None
    linked_advising_meeting_id: int | None = None
    source: str | None = None
    outcome_tag: str | None = None
    outcome_note: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    note: str | None = None
    linked_student_id: int | None = None
    linked_course_id: int | None = None
    linked_interaction_id: int | None = None
    linked_advising_meeting_id: int | None = None
    outcome_tag: str | None = None
    outcome_note: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None
    note: str | None
    linked_student_id: int | None
    linked_course_id: int | None
    linked_interaction_id: int | None
    linked_advising_meeting_id: int | None
    source: str
    outcome_tag: str | None
    outcome_note: str | None
    created_at: datetime
    updated_at: datetime


class TaskBulkUpdate(BaseModel):
    task_ids: list[int]
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    due_shift_days: int | None = None
    outcome_tag: str | None = None
    outcome_note: str | None = None


class WorkflowBenchmarkCreate(BaseModel):
    workflow: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=80)
    duration_ms: int | None = None
    context_json: dict = Field(default_factory=dict)
