from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    Course,
    RubricCriterion,
    RubricCriterionRating,
    RubricEvaluation,
    RubricEvaluationItem,
    RubricTemplate,
    StudentProfile,
)
from app.db.session import get_db
from app.schemas.rubrics import (
    RubricCriterionCreate,
    RubricCriterionRatingCreate,
    RubricCriterionRatingUpdate,
    RubricCriterionUpdate,
    RubricEvaluationCreate,
    RubricTemplateCreate,
    RubricTemplateUpdate,
)

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


def _rubric_evaluation_count(db: Session, rubric_id: int) -> int:
    return int(db.scalar(select(func.count()).select_from(RubricEvaluation).where(RubricEvaluation.rubric_id == rubric_id)) or 0)


def _serialize_rubric(rubric: RubricTemplate, evaluation_count: int = 0) -> dict:
    criteria = sorted(rubric.criteria, key=lambda criterion: (criterion.display_order, criterion.id))
    return {
        "id": rubric.id,
        "name": rubric.name,
        "description": rubric.description,
        "max_points": rubric.max_points,
        "archived_at": rubric.archived_at.isoformat() if rubric.archived_at else None,
        "is_archived": rubric.archived_at is not None,
        "evaluation_count": evaluation_count,
        "can_delete": evaluation_count == 0,
        "criteria": [
            {
                "id": criterion.id,
                "title": criterion.title,
                "criterion_type": criterion.criterion_type.value,
                "max_points": criterion.max_points,
                "is_required": criterion.is_required,
                "prompt": criterion.prompt,
                "display_order": criterion.display_order,
                "ratings": [
                    {
                        "id": rating.id,
                        "title": rating.title,
                        "description": rating.description,
                        "points": rating.points,
                        "display_order": rating.display_order,
                    }
                    for rating in sorted(criterion.ratings, key=lambda item: (item.display_order, item.id))
                ],
            }
            for criterion in criteria
        ],
    }


def _serialize_evaluation(
    evaluation: RubricEvaluation,
    rubric_map: dict[int, RubricTemplate],
    student_map: dict[int, StudentProfile],
    course_map: dict[int, Course],
    assignment_map: dict[int, Assignment],
) -> dict:
    rubric = rubric_map.get(evaluation.rubric_id)
    student = student_map.get(evaluation.student_profile_id) if evaluation.student_profile_id else None
    course = course_map.get(evaluation.course_id) if evaluation.course_id else None
    assignment = assignment_map.get(evaluation.assignment_id) if evaluation.assignment_id else None
    criteria_by_id = {criterion.id: criterion for criterion in rubric.criteria} if rubric else {}
    ratings_by_id = {
        rating.id: rating
        for criterion in criteria_by_id.values()
        for rating in criterion.ratings
    }

    return {
        "id": evaluation.id,
        "rubric_id": evaluation.rubric_id,
        "rubric_name": rubric.name if rubric else None,
        "rubric_max_points": rubric.max_points if rubric else None,
        "student_profile_id": evaluation.student_profile_id,
        "student_name": f"{student.first_name} {student.last_name}".strip() if student else None,
        "course_id": evaluation.course_id,
        "course_name": course.name if course else None,
        "assignment_id": evaluation.assignment_id,
        "assignment_title": assignment.title if assignment else None,
        "evaluator_notes": evaluation.evaluator_notes,
        "total_points": evaluation.total_points,
        "created_at": evaluation.created_at.isoformat(),
        "items": [
            {
                "id": item.id,
                "criterion_id": item.criterion_id,
                "criterion_title": criteria_by_id[item.criterion_id].title if item.criterion_id in criteria_by_id else None,
                "criterion_type": criteria_by_id[item.criterion_id].criterion_type.value if item.criterion_id in criteria_by_id else None,
                "criterion_max_points": criteria_by_id[item.criterion_id].max_points if item.criterion_id in criteria_by_id else None,
                "rating_id": item.rating_id,
                "rating_title": ratings_by_id[item.rating_id].title if item.rating_id in ratings_by_id else None,
                "rating_description": ratings_by_id[item.rating_id].description if item.rating_id in ratings_by_id else None,
                "points_awarded": item.points_awarded,
                "is_checked": item.is_checked,
                "narrative_comment": item.narrative_comment,
            }
            for item in sorted(
                evaluation.items,
                key=lambda row: (
                    criteria_by_id[row.criterion_id].display_order if row.criterion_id in criteria_by_id else 0,
                    row.id,
                ),
            )
        ],
    }


@router.get("/targets")
def rubric_targets(db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    courses = db.scalars(select(Course).order_by(Course.name.asc())).all()
    assignments = db.scalars(select(Assignment).order_by(Assignment.title.asc())).all()

    return {
        "students": [
            {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}".strip(),
            }
            for student in students
        ],
        "courses": [
            {
                "id": course.id,
                "name": course.name,
            }
            for course in courses
        ],
        "assignments": [
            {
                "id": assignment.id,
                "title": assignment.title,
                "course_id": assignment.course_id,
            }
            for assignment in assignments
        ],
    }


@router.get("/evaluations")
def list_rubric_evaluations(
    rubric_id: int | None = Query(default=None),
    student_profile_id: int | None = Query(default=None),
    course_id: int | None = Query(default=None),
    assignment_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(RubricEvaluation)
    if rubric_id is not None:
        query = query.where(RubricEvaluation.rubric_id == rubric_id)
    if student_profile_id is not None:
        query = query.where(RubricEvaluation.student_profile_id == student_profile_id)
    if course_id is not None:
        query = query.where(RubricEvaluation.course_id == course_id)
    if assignment_id is not None:
        query = query.where(RubricEvaluation.assignment_id == assignment_id)

    evaluations = db.scalars(query.order_by(RubricEvaluation.created_at.desc(), RubricEvaluation.id.desc()).limit(limit)).all()

    rubric_ids = {evaluation.rubric_id for evaluation in evaluations}
    student_ids = {evaluation.student_profile_id for evaluation in evaluations if evaluation.student_profile_id is not None}
    course_ids = {evaluation.course_id for evaluation in evaluations if evaluation.course_id is not None}
    assignment_ids = {evaluation.assignment_id for evaluation in evaluations if evaluation.assignment_id is not None}

    rubric_map = {
        rubric.id: rubric
        for rubric in (db.scalars(select(RubricTemplate).where(RubricTemplate.id.in_(rubric_ids))).all() if rubric_ids else [])
    }
    student_map = {
        student.id: student
        for student in (
            db.scalars(select(StudentProfile).where(StudentProfile.id.in_(student_ids))).all() if student_ids else []
        )
    }
    course_map = {
        course.id: course
        for course in (db.scalars(select(Course).where(Course.id.in_(course_ids))).all() if course_ids else [])
    }
    assignment_map = {
        assignment.id: assignment
        for assignment in (
            db.scalars(select(Assignment).where(Assignment.id.in_(assignment_ids))).all() if assignment_ids else []
        )
    }

    return [
        _serialize_evaluation(evaluation, rubric_map, student_map, course_map, assignment_map)
        for evaluation in evaluations
    ]


@router.get("/evaluations/{evaluation_id}")
def get_rubric_evaluation(evaluation_id: int, db: Session = Depends(get_db)) -> dict:
    evaluation = db.get(RubricEvaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    rubric = db.get(RubricTemplate, evaluation.rubric_id)
    student = db.get(StudentProfile, evaluation.student_profile_id) if evaluation.student_profile_id else None
    course = db.get(Course, evaluation.course_id) if evaluation.course_id else None
    assignment = db.get(Assignment, evaluation.assignment_id) if evaluation.assignment_id else None

    return _serialize_evaluation(
        evaluation,
        {rubric.id: rubric} if rubric else {},
        {student.id: student} if student else {},
        {course.id: course} if course else {},
        {assignment.id: assignment} if assignment else {},
    )


@router.get("/")
def list_rubrics(
    archive_state: str = Query(default="active", pattern="^(active|archived|all)$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(RubricTemplate)
    if archive_state == "active":
        query = query.where(RubricTemplate.archived_at.is_(None))
    elif archive_state == "archived":
        query = query.where(RubricTemplate.archived_at.is_not(None))

    rubrics = db.scalars(query.order_by(RubricTemplate.name.asc())).all()
    evaluation_counts = {
        rubric_id: int(count)
        for rubric_id, count in db.execute(
            select(RubricEvaluation.rubric_id, func.count(RubricEvaluation.id)).group_by(RubricEvaluation.rubric_id)
        ).all()
    }
    return [_serialize_rubric(rubric, evaluation_counts.get(rubric.id, 0)) for rubric in rubrics]


@router.get("/{rubric_id}")
def get_rubric(rubric_id: int, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id))


@router.post("/")
def create_rubric(payload: RubricTemplateCreate, db: Session = Depends(get_db)) -> dict:
    rubric = RubricTemplate(**payload.model_dump())
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return _serialize_rubric(rubric, 0)


@router.patch("/{rubric_id}")
def update_rubric(rubric_id: int, payload: RubricTemplateUpdate, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rubric, field, value)

    db.commit()
    db.refresh(rubric)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id))


@router.delete("/{rubric_id}")
def delete_rubric(rubric_id: int, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    evaluation_count = _rubric_evaluation_count(db, rubric_id)
    if evaluation_count > 0:
        raise HTTPException(status_code=409, detail="Rubric has student evaluations and must be archived instead of deleted")
    db.delete(rubric)
    db.commit()
    return {"deleted": True, "rubric_id": rubric_id}


@router.post("/{rubric_id}/archive")
def archive_rubric(rubric_id: int, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    rubric.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rubric)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id))


@router.post("/{rubric_id}/restore")
def restore_rubric(rubric_id: int, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    rubric.archived_at = None
    db.commit()
    db.refresh(rubric)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id))


@router.post("/{rubric_id}/criteria")
def add_rubric_criterion(rubric_id: int, payload: RubricCriterionCreate, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    display_order = payload.display_order
    if display_order is None:
        existing_orders = [criterion.display_order for criterion in rubric.criteria]
        display_order = (max(existing_orders) + 1) if existing_orders else 1

    criterion = RubricCriterion(rubric_id=rubric_id, **payload.model_dump(exclude={"display_order"}), display_order=display_order)
    db.add(criterion)
    db.commit()
    db.refresh(rubric)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id) if rubric else 0)


@router.patch("/{rubric_id}/criteria/{criterion_id}")
def update_rubric_criterion(
    rubric_id: int,
    criterion_id: int,
    payload: RubricCriterionUpdate,
    db: Session = Depends(get_db),
) -> dict:
    criterion = db.get(RubricCriterion, criterion_id)
    if not criterion or criterion.rubric_id != rubric_id:
        raise HTTPException(status_code=404, detail="Criterion not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(criterion, field, value)

    db.commit()
    rubric = db.get(RubricTemplate, rubric_id)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id) if rubric else 0)


@router.delete("/{rubric_id}/criteria/{criterion_id}")
def delete_rubric_criterion(rubric_id: int, criterion_id: int, db: Session = Depends(get_db)) -> dict:
    criterion = db.get(RubricCriterion, criterion_id)
    if not criterion or criterion.rubric_id != rubric_id:
        raise HTTPException(status_code=404, detail="Criterion not found")
    db.delete(criterion)
    db.commit()
    rubric = db.get(RubricTemplate, rubric_id)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id) if rubric else 0)


@router.post("/{rubric_id}/criteria/{criterion_id}/ratings")
def add_rubric_rating(
    rubric_id: int,
    criterion_id: int,
    payload: RubricCriterionRatingCreate,
    db: Session = Depends(get_db),
) -> dict:
    criterion = db.get(RubricCriterion, criterion_id)
    if not criterion or criterion.rubric_id != rubric_id:
        raise HTTPException(status_code=404, detail="Criterion not found")

    display_order = payload.display_order
    if display_order is None:
        existing_orders = [rating.display_order for rating in criterion.ratings]
        display_order = (max(existing_orders) + 1) if existing_orders else 1

    rating = RubricCriterionRating(
        criterion_id=criterion_id,
        **payload.model_dump(exclude={"display_order"}),
        display_order=display_order,
    )
    db.add(rating)
    db.commit()
    rubric = db.get(RubricTemplate, rubric_id)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id) if rubric else 0)


@router.patch("/{rubric_id}/criteria/{criterion_id}/ratings/{rating_id}")
def update_rubric_rating(
    rubric_id: int,
    criterion_id: int,
    rating_id: int,
    payload: RubricCriterionRatingUpdate,
    db: Session = Depends(get_db),
) -> dict:
    criterion = db.get(RubricCriterion, criterion_id)
    if not criterion or criterion.rubric_id != rubric_id:
        raise HTTPException(status_code=404, detail="Criterion not found")

    rating = db.get(RubricCriterionRating, rating_id)
    if not rating or rating.criterion_id != criterion_id:
        raise HTTPException(status_code=404, detail="Rating not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(rating, field, value)

    db.commit()
    rubric = db.get(RubricTemplate, rubric_id)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id) if rubric else 0)


@router.delete("/{rubric_id}/criteria/{criterion_id}/ratings/{rating_id}")
def delete_rubric_rating(rubric_id: int, criterion_id: int, rating_id: int, db: Session = Depends(get_db)) -> dict:
    criterion = db.get(RubricCriterion, criterion_id)
    if not criterion or criterion.rubric_id != rubric_id:
        raise HTTPException(status_code=404, detail="Criterion not found")

    rating = db.get(RubricCriterionRating, rating_id)
    if not rating or rating.criterion_id != criterion_id:
        raise HTTPException(status_code=404, detail="Rating not found")

    db.delete(rating)
    db.commit()
    rubric = db.get(RubricTemplate, rubric_id)
    return _serialize_rubric(rubric, _rubric_evaluation_count(db, rubric.id) if rubric else 0)


@router.post("/evaluations")
def create_rubric_evaluation(payload: RubricEvaluationCreate, db: Session = Depends(get_db)) -> dict:
    rubric = db.get(RubricTemplate, payload.rubric_id)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    if rubric.archived_at is not None:
        raise HTTPException(status_code=400, detail="Archived rubrics must be restored before scoring")

    criteria_by_id = {criterion.id: criterion for criterion in rubric.criteria}

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

    calculated_total = 0.0
    has_points = False

    for item in payload.items:
        criterion = criteria_by_id.get(item.criterion_id)
        if not criterion:
            raise HTTPException(status_code=400, detail=f"Criterion {item.criterion_id} does not belong to this rubric")

        rating = None
        if item.rating_id is not None:
            rating = db.get(RubricCriterionRating, item.rating_id)
            if not rating or rating.criterion_id != criterion.id:
                raise HTTPException(status_code=400, detail=f"Rating {item.rating_id} does not belong to criterion {criterion.id}")

        points_awarded = item.points_awarded
        if points_awarded is None and rating and rating.points is not None:
            points_awarded = rating.points

        if points_awarded is None and criterion.criterion_type.value == "checkbox" and item.is_checked:
            points_awarded = criterion.max_points if criterion.max_points is not None else 1.0

        if points_awarded is not None:
            calculated_total += float(points_awarded)
            has_points = True

        db.add(
            RubricEvaluationItem(
                evaluation_id=evaluation.id,
                criterion_id=criterion.id,
                rating_id=item.rating_id,
                points_awarded=points_awarded,
                is_checked=item.is_checked,
                narrative_comment=item.narrative_comment,
            )
        )

    if payload.total_points is None:
        evaluation.total_points = round(calculated_total, 2) if has_points else None

    db.commit()
    db.refresh(evaluation)

    student = db.get(StudentProfile, evaluation.student_profile_id) if evaluation.student_profile_id else None
    course = db.get(Course, evaluation.course_id) if evaluation.course_id else None
    assignment = db.get(Assignment, evaluation.assignment_id) if evaluation.assignment_id else None

    return _serialize_evaluation(
        evaluation,
        {rubric.id: rubric},
        {student.id: student} if student else {},
        {course.id: course} if course else {},
        {assignment.id: assignment} if assignment else {},
    )
