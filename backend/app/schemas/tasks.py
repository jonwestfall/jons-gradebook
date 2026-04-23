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
    created_at: datetime
    updated_at: datetime

