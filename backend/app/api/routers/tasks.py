from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session

from app.db.models import AppOption, Course, StudentProfile, Task, TaskPriority, TaskStatus
from app.db.session import get_db
from app.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.services.risk import compute_risk_for_students, should_trigger_intervention

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/targets")
def task_targets(db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    courses = db.scalars(select(Course).order_by(Course.name.asc())).all()
    return {
        "students": [
            {"id": student.id, "name": f"{student.first_name} {student.last_name}".strip(), "email": student.email}
            for student in students
        ],
        "courses": [{"id": course.id, "name": course.name, "section_name": course.section_name} for course in courses],
    }


@router.post("/rules/run")
def run_intervention_rules(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    option = db.scalar(select(AppOption).where(AppOption.key == "intervention_rules"))
    rules = option.value_json if option and isinstance(option.value_json, list) else []
    if not rules:
        # Default single-instructor rule.
        rules = [
            {
                "name": "missing-and-low-grade",
                "min_score": 60,
                "priority": "high",
                "due_days": 2,
                "template": "Follow up with student on missing work and recovery plan.",
            }
        ]

    risk_rows = compute_risk_for_students(db)
    created = 0
    skipped = 0
    for risk in risk_rows:
        for rule in rules:
            min_score = int(rule.get("min_score", 60))
            if not should_trigger_intervention(risk, min_score=min_score):
                continue

            title = f"Intervention: {risk.student_name}"
            existing = db.scalar(
                select(Task).where(
                    Task.title == title,
                    Task.linked_student_id == risk.student_id,
                    Task.status.in_([TaskStatus.open, TaskStatus.in_progress]),
                )
            )
            if existing:
                skipped += 1
                continue

            due_days = int(rule.get("due_days", 2))
            priority = rule.get("priority", "high")
            try:
                parsed_priority = TaskPriority(priority)
            except ValueError:
                parsed_priority = TaskPriority.high

            note_template = str(rule.get("template") or "").strip()
            note = note_template or "Reach out with support and next-step plan."
            note = f"{note}\nRisk reasons: {', '.join(risk.reasons)}"
            task = Task(
                title=title,
                status=TaskStatus.open,
                priority=parsed_priority,
                due_at=now + timedelta(days=due_days),
                note=note,
                linked_student_id=risk.student_id,
                source="rule_engine",
            )
            db.add(task)
            created += 1

    db.commit()
    return {"created_count": created, "skipped_count": skipped, "evaluated_students": len(risk_rows)}


@router.get("/")
def list_tasks(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    student_id: int | None = Query(default=None),
    course_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="due_at"),
    sort_order: str = Query(default="asc"),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(Task)

    if status:
        try:
            parsed = TaskStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status") from exc
        query = query.where(Task.status == parsed)

    if priority:
        try:
            parsed = TaskPriority(priority)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid priority") from exc
        query = query.where(Task.priority == parsed)

    if student_id is not None:
        query = query.where(Task.linked_student_id == student_id)
    if course_id is not None:
        query = query.where(Task.linked_course_id == course_id)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Task.title.ilike(pattern), Task.note.ilike(pattern)))

    sort_fields = {
        "due_at": Task.due_at,
        "priority": Task.priority,
        "created_at": Task.created_at,
        "updated_at": Task.updated_at,
    }
    field = sort_fields.get(sort_by, Task.due_at)
    direction = asc if sort_order.lower() == "asc" else desc
    rows = db.scalars(query.order_by(direction(field), desc(Task.id)).limit(limit)).all()
    return [_task_payload(task) for task in rows]


@router.post("/", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    if payload.linked_student_id is not None and not db.get(StudentProfile, payload.linked_student_id):
        raise HTTPException(status_code=404, detail="Linked student not found")
    if payload.linked_course_id is not None and not db.get(Course, payload.linked_course_id):
        raise HTTPException(status_code=404, detail="Linked course not found")

    task = Task(
        title=payload.title.strip(),
        status=payload.status,
        priority=payload.priority,
        due_at=payload.due_at,
        note=payload.note,
        linked_student_id=payload.linked_student_id,
        linked_course_id=payload.linked_course_id,
        linked_interaction_id=payload.linked_interaction_id,
        linked_advising_meeting_id=payload.linked_advising_meeting_id,
        source=(payload.source or "manual").strip() or "manual",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)

    if "linked_student_id" in updates and updates["linked_student_id"] is not None:
        if not db.get(StudentProfile, int(updates["linked_student_id"])):
            raise HTTPException(status_code=404, detail="Linked student not found")
    if "linked_course_id" in updates and updates["linked_course_id"] is not None:
        if not db.get(Course, int(updates["linked_course_id"])):
            raise HTTPException(status_code=404, detail="Linked course not found")

    for key, value in updates.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"deleted": True, "task_id": task_id}


def _task_payload(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "note": task.note,
        "linked_student_id": task.linked_student_id,
        "linked_course_id": task.linked_course_id,
        "linked_interaction_id": task.linked_interaction_id,
        "linked_advising_meeting_id": task.linked_advising_meeting_id,
        "source": task.source,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
