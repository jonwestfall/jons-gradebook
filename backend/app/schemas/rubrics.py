from pydantic import BaseModel, Field

from app.db.models import RubricCriterionType


class RubricTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    max_points: float | None = None


class RubricCriterionCreate(BaseModel):
    title: str
    criterion_type: RubricCriterionType
    max_points: float | None = None
    is_required: bool = False
    prompt: str | None = None


class RubricEvaluationCreate(BaseModel):
    rubric_id: int
    student_profile_id: int | None = None
    course_id: int | None = None
    assignment_id: int | None = None
    evaluator_notes: str | None = None
    total_points: float | None = None
    items: list[dict] = Field(default_factory=list)
