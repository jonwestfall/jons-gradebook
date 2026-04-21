from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    RubricCriterion,
    RubricEvaluation,
    RubricEvaluationItem,
    RubricTemplate,
)
from app.db.session import get_db
from app.schemas.rubrics import RubricCriterionCreate, RubricEvaluationCreate, RubricTemplateCreate

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.get("/")
def list_rubrics(db: Session = Depends(get_db)) -> list[dict]:
    rubrics = db.scalars(select(RubricTemplate).order_by(RubricTemplate.name.asc())).all()
    return [
        {
            "id": rubric.id,
            "name": rubric.name,
            "description": rubric.description,
            "max_points": rubric.max_points,
            "criteria": [
                {
                    "id": criterion.id,
                    "title": criterion.title,
                    "criterion_type": criterion.criterion_type.value,
                    "max_points": criterion.max_points,
                    "is_required": criterion.is_required,
                    "prompt": criterion.prompt,
                }
                for criterion in rubric.criteria
            ],
        }
        for rubric in rubrics
    ]


@router.post("/")
def create_rubric(payload: RubricTemplateCreate, db: Session = Depends(get_db)) -> dict:
    rubric = RubricTemplate(**payload.model_dump())
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return {
        "id": rubric.id,
        "name": rubric.name,
        "description": rubric.description,
        "max_points": rubric.max_points,
    }


@router.post("/{rubric_id}/criteria")
def add_rubric_criterion(rubric_id: int, payload: RubricCriterionCreate, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    criterion = RubricCriterion(rubric_id=rubric_id, **payload.model_dump())
    db.add(criterion)
    db.commit()
    db.refresh(criterion)
    return {
        "id": criterion.id,
        "rubric_id": criterion.rubric_id,
        "title": criterion.title,
        "criterion_type": criterion.criterion_type.value,
        "max_points": criterion.max_points,
        "is_required": criterion.is_required,
    }


@router.post("/evaluations")
def create_rubric_evaluation(payload: RubricEvaluationCreate, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, payload.rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    evaluation = RubricEvaluation(
        rubric_id=payload.rubric_id,
        student_profile_id=payload.student_profile_id,
        course_id=payload.course_id,
        assignment_id=payload.assignment_id,
        evaluator_notes=payload.evaluator_notes,
        total_points=payload.total_points,
    )
    db.add(evaluation)
    db.flush()

    for item in payload.items:
        criterion_id = item.get("criterion_id")
        if not criterion_id:
            continue
        db.add(
            RubricEvaluationItem(
                evaluation_id=evaluation.id,
                criterion_id=criterion_id,
                points_awarded=item.get("points_awarded"),
                is_checked=item.get("is_checked"),
                narrative_comment=item.get("narrative_comment"),
            )
        )

    db.commit()
    db.refresh(evaluation)
    return {
        "id": evaluation.id,
        "rubric_id": evaluation.rubric_id,
        "student_profile_id": evaluation.student_profile_id,
        "course_id": evaluation.course_id,
        "assignment_id": evaluation.assignment_id,
        "total_points": evaluation.total_points,
    }
