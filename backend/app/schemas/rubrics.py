from pydantic import BaseModel, Field

from app.db.models import RubricCriterionType


class RubricTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    max_points: float | None = None


class RubricTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    max_points: float | None = None


class RubricCriterionCreate(BaseModel):
    title: str
    criterion_type: RubricCriterionType
    max_points: float | None = None
    is_required: bool = False
    prompt: str | None = None
    display_order: int | None = None


class RubricCriterionUpdate(BaseModel):
    title: str | None = None
    criterion_type: RubricCriterionType | None = None
    max_points: float | None = None
    is_required: bool | None = None
    prompt: str | None = None
    display_order: int | None = None


class RubricCriterionRatingCreate(BaseModel):
    title: str
    description: str | None = None
    points: float | None = None
    display_order: int | None = None


class RubricCriterionRatingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    points: float | None = None
    display_order: int | None = None


class RubricEvaluationItemCreate(BaseModel):
    criterion_id: int
    rating_id: int | None = None
    points_awarded: float | None = None
    is_checked: bool | None = None
    narrative_comment: str | None = None


class RubricEvaluationCreate(BaseModel):
    rubric_id: int
    student_profile_id: int | None = None
    course_id: int | None = None
    assignment_id: int | None = None
    evaluator_notes: str | None = None
    total_points: float | None = None
    items: list[RubricEvaluationItemCreate] = Field(default_factory=list)
