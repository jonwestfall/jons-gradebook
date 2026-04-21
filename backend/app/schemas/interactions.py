from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import InteractionType


class InteractionCreate(BaseModel):
    student_profile_id: int | None = None
    advisee_id: int | None = None
    interaction_type: InteractionType
    occurred_at: datetime
    summary: str = Field(min_length=1, max_length=255)
    notes: str | None = None
    metadata_json: dict = Field(default_factory=dict)
