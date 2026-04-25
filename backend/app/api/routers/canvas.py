from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CanvasAssignmentSnapshot,
    CanvasCourseSnapshot,
    CanvasEnrollmentSnapshot,
    CanvasSubmissionSnapshot,
    CanvasSyncConflict,
    CanvasSyncConflictStatus,
    CanvasSyncEntityType,
    CanvasSyncEvent,
    CanvasSyncEventAction,
    CanvasSyncRun,
    GradeEntryAudit,
    GradeSource,
    GradeStatus,
)
from app.db.session import get_db
from app.schemas.canvas import (
    CanvasCourseSelectionUpdateRequest,
    CanvasSyncConflictResolutionRequest,
    CanvasStudentFieldMappingUpdateRequest,
    CanvasSyncRequest,
)
from app.services.canvas.selection import (
    discover_and_cache_courses,
    list_course_selections,
    selected_course_ids,
    set_selected_courses,
)
from app.services.canvas.student_mapping import (
    COMMON_SOURCE_PATHS,
    DEFAULT_MAPPING,
    list_mapping_config,
    preview_student_metadata,
    set_mapping_config,
)
from app.services.canvas.sync import run_canvas_sync

router = APIRouter(prefix="/canvas", tags=["canvas"])


def _serialize_conflict(conflict: CanvasSyncConflict) -> dict:
    return {
        "id": conflict.id,
        "sync_run_id": conflict.sync_run_id,
        "course_id": conflict.course_id,
        "course_name": conflict.course.name if conflict.course else None,
        "assignment_id": conflict.assignment_id,
        "assignment_title": conflict.assignment.title if conflict.assignment else None,
        "student_id": conflict.student_id,
        "student_name": f"{conflict.student.first_name} {conflict.student.last_name}".strip()
        if conflict.student
        else None,
        "grade_entry_id": conflict.grade_entry_id,
        "canvas_course_id": conflict.canvas_course_id,
        "canvas_assignment_id": conflict.canvas_assignment_id,
        "canvas_user_id": conflict.canvas_user_id,
        "local": {
            "score": conflict.local_score,
            "status": conflict.local_status,
            "source": conflict.local_source,
        },
        "canvas": {
            "score": conflict.canvas_score,
            "status": conflict.canvas_status,
        },
        "status": conflict.status.value,
        "rationale": conflict.rationale,
        "resolved_at": conflict.resolved_at.isoformat() if conflict.resolved_at else None,
        "created_at": conflict.created_at.isoformat(),
        "updated_at": conflict.updated_at.isoformat(),
    }


def _grade_snapshot(entry) -> dict:
    if not entry:
        return {}
    return {
        "score": entry.score,
        "letter_grade": entry.letter_grade,
        "completion_status": entry.completion_status.value if entry.completion_status else None,
        "status": entry.status.value if entry.status else None,
        "source": entry.source.value if entry.source else None,
        "submitted_at": entry.submitted_at.isoformat() if entry.submitted_at else None,
        "snapshot_run_id": entry.snapshot_run_id,
    }


def _snapshot_identity(entity_type: str, snapshot) -> str:
    if entity_type == "course":
        return snapshot.canvas_course_id
    if entity_type == "assignment":
        return f"{snapshot.canvas_course_id}:{snapshot.canvas_assignment_id}"
    if entity_type == "enrollment":
        return f"{snapshot.canvas_course_id}:{snapshot.canvas_user_id}"
    return f"{snapshot.canvas_course_id}:{snapshot.canvas_assignment_id}:{snapshot.canvas_user_id}"


def _snapshot_payload(entity_type: str, snapshot) -> dict:
    if entity_type == "course":
        return {
            "canvas_course_id": snapshot.canvas_course_id,
            "name": snapshot.name,
            "section_name": snapshot.section_name,
        }
    if entity_type == "assignment":
        return {
            "canvas_course_id": snapshot.canvas_course_id,
            "canvas_assignment_id": snapshot.canvas_assignment_id,
            "name": snapshot.name,
            "due_at": snapshot.due_at.isoformat() if snapshot.due_at else None,
            "points_possible": snapshot.points_possible,
        }
    if entity_type == "enrollment":
        return {
            "canvas_course_id": snapshot.canvas_course_id,
            "canvas_enrollment_id": snapshot.canvas_enrollment_id,
            "canvas_user_id": snapshot.canvas_user_id,
            "role": snapshot.role,
        }
    return {
        "canvas_course_id": snapshot.canvas_course_id,
        "canvas_assignment_id": snapshot.canvas_assignment_id,
        "canvas_user_id": snapshot.canvas_user_id,
        "score": snapshot.score,
        "submitted_at": snapshot.submitted_at.isoformat() if snapshot.submitted_at else None,
    }


def _changed_fields(before: dict | None, after: dict | None) -> list[str]:
    if before is None or after is None:
        return []
    keys = sorted(set(before) | set(after))
    return [key for key in keys if before.get(key) != after.get(key)]


@router.post("/sync")
def trigger_sync(payload: CanvasSyncRequest, db: Session = Depends(get_db)) -> dict:
    run = run_canvas_sync(
        db,
        trigger_type=payload.trigger_type,
        snapshot_label=payload.snapshot_label,
        canvas_course_ids=payload.canvas_course_ids,
    )
    return {
        "id": run.id,
        "trigger_type": run.trigger_type.value,
        "status": run.status.value,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "snapshot_label": run.snapshot_label,
        "error_message": run.error_message,
    }


@router.get("/courses/discover")
def discover_canvas_courses(db: Session = Depends(get_db)) -> list[dict]:
    try:
        courses = discover_and_cache_courses(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [
        {
            "canvas_course_id": row.canvas_course_id,
            "name": row.name,
            "course_code": row.course_code,
            "term_name": row.term_name,
            "term_start_at": row.term_start_at.isoformat() if row.term_start_at else None,
            "term_end_at": row.term_end_at.isoformat() if row.term_end_at else None,
            "is_selected": row.is_selected,
        }
        for row in courses
    ]


@router.get("/courses/selected")
def get_selected_canvas_courses(db: Session = Depends(get_db)) -> list[dict]:
    courses = [row for row in list_course_selections(db) if row.is_selected]
    return [
        {
            "canvas_course_id": row.canvas_course_id,
            "name": row.name,
            "course_code": row.course_code,
            "term_name": row.term_name,
            "term_start_at": row.term_start_at.isoformat() if row.term_start_at else None,
            "term_end_at": row.term_end_at.isoformat() if row.term_end_at else None,
        }
        for row in courses
    ]


@router.put("/courses/selected")
def update_selected_canvas_courses(payload: CanvasCourseSelectionUpdateRequest, db: Session = Depends(get_db)) -> dict:
    try:
        courses = set_selected_courses(db, payload.canvas_course_ids, mode=payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    selected = [row for row in courses if row.is_selected]
    return {
        "mode": payload.mode,
        "selected_count": len(selected),
        "selected_course_ids": [row.canvas_course_id for row in selected],
    }


@router.get("/student-metadata/mapping")
def get_student_metadata_mapping(db: Session = Depends(get_db)) -> dict:
    return {
        "mappings": list_mapping_config(db),
        "common_source_paths": COMMON_SOURCE_PATHS,
        "default_mapping": DEFAULT_MAPPING,
    }


@router.put("/student-metadata/mapping")
def update_student_metadata_mapping(payload: CanvasStudentFieldMappingUpdateRequest, db: Session = Depends(get_db)) -> dict:
    try:
        mapping = set_mapping_config(db, target_field=payload.target_field, source_paths=payload.source_paths)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return mapping


@router.get("/student-metadata/preview")
def get_student_metadata_preview(
    canvas_course_id: str | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=25),
    db: Session = Depends(get_db),
) -> dict:
    target_course_id = canvas_course_id
    if not target_course_id:
        selected = selected_course_ids(db)
        if not selected:
            raise HTTPException(
                status_code=400,
                detail="No selected Canvas courses available for metadata preview. Choose classes first.",
            )
        target_course_id = selected[0]

    try:
        return preview_student_metadata(canvas_course_id=target_course_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/sync/runs")
def list_sync_runs(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(CanvasSyncRun).order_by(CanvasSyncRun.started_at.desc()).limit(100)).all()
    return [
        {
            "id": run.id,
            "trigger_type": run.trigger_type.value,
            "status": run.status.value,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "snapshot_label": run.snapshot_label,
            "error_message": run.error_message,
            "event_counts": {
                "created": sum(1 for event in run.events if event.action.value == "created"),
                "updated": sum(1 for event in run.events if event.action.value == "updated"),
                "deleted": sum(1 for event in run.events if event.action.value == "deleted"),
            },
        }
        for run in runs
    ]


@router.get("/sync/runs/{run_id}")
def get_sync_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.get(CanvasSyncRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    return {
        "id": run.id,
        "trigger_type": run.trigger_type.value,
        "status": run.status.value,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "snapshot_label": run.snapshot_label,
        "error_message": run.error_message,
        "snapshot_counts": {
            "courses": len(run.course_snapshots),
            "assignments": len(run.assignment_snapshots),
            "enrollments": len(run.enrollment_snapshots),
            "submissions": len(run.submission_snapshots),
        },
        "event_counts": {
            "created": sum(1 for event in run.events if event.action.value == "created"),
            "updated": sum(1 for event in run.events if event.action.value == "updated"),
            "deleted": sum(1 for event in run.events if event.action.value == "deleted"),
        },
        "recent_events": [
            {
                "id": event.id,
                "entity_type": event.entity_type.value,
                "action": event.action.value,
                "canvas_course_id": event.canvas_course_id,
                "canvas_item_id": event.canvas_item_id,
                "local_item_id": event.local_item_id,
                "detail": event.detail,
                "created_at": event.created_at.isoformat(),
            }
            for event in sorted(run.events, key=lambda item: item.created_at, reverse=True)[:40]
        ],
    }


@router.get("/sync/runs/{run_id}/events")
def list_sync_run_events(
    run_id: int,
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    run = db.get(CanvasSyncRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    query = select(CanvasSyncEvent).where(CanvasSyncEvent.sync_run_id == run_id).order_by(CanvasSyncEvent.created_at.desc())
    if action:
        try:
            parsed_action = CanvasSyncEventAction(action)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid event action") from exc
        query = query.where(CanvasSyncEvent.action == parsed_action)
    if entity_type:
        try:
            parsed_entity = CanvasSyncEntityType(entity_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid entity type") from exc
        query = query.where(CanvasSyncEvent.entity_type == parsed_entity)
    all_events = db.scalars(query).all()
    total = len(all_events)
    events = all_events[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": [
            {
                "id": event.id,
                "entity_type": event.entity_type.value,
                "action": event.action.value,
                "canvas_course_id": event.canvas_course_id,
                "canvas_item_id": event.canvas_item_id,
                "local_item_id": event.local_item_id,
                "detail": event.detail,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }


@router.get("/sync/runs/{run_id}/diff")
def get_sync_run_diff(
    run_id: int,
    entity_type: str = Query(default="submission"),
    changed_only: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    run = db.get(CanvasSyncRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")

    model_by_type = {
        "course": CanvasCourseSnapshot,
        "assignment": CanvasAssignmentSnapshot,
        "enrollment": CanvasEnrollmentSnapshot,
        "submission": CanvasSubmissionSnapshot,
    }
    model = model_by_type.get(entity_type)
    if model is None:
        raise HTTPException(status_code=400, detail="Invalid diff entity type")

    previous_run = db.scalar(
        select(CanvasSyncRun)
        .where(CanvasSyncRun.started_at < run.started_at)
        .order_by(CanvasSyncRun.started_at.desc())
        .limit(1)
    )

    current_rows = db.scalars(select(model).where(model.sync_run_id == run_id)).all()
    previous_rows = db.scalars(select(model).where(model.sync_run_id == previous_run.id)).all() if previous_run else []
    previous_by_identity = {_snapshot_identity(entity_type, row): row for row in previous_rows}

    rows = []
    for current in current_rows:
        identity = _snapshot_identity(entity_type, current)
        before = previous_by_identity.get(identity)
        before_payload = _snapshot_payload(entity_type, before) if before else None
        after_payload = _snapshot_payload(entity_type, current)
        changed_fields = _changed_fields(before_payload, after_payload)
        change_type = "created" if before is None else "updated" if changed_fields else "unchanged"
        if changed_only and change_type == "unchanged":
            continue
        rows.append(
            {
                "identity": identity,
                "change_type": change_type,
                "changed_fields": changed_fields,
                "before": before_payload,
                "after": after_payload,
            }
        )
        if len(rows) >= limit:
            break

    return {
        "run_id": run.id,
        "previous_run_id": previous_run.id if previous_run else None,
        "entity_type": entity_type,
        "changed_only": changed_only,
        "rows": rows,
    }


@router.get("/sync/runs/{run_id}/conflicts")
def list_sync_run_conflicts(run_id: int, db: Session = Depends(get_db)) -> list[dict]:
    if not db.get(CanvasSyncRun, run_id):
        raise HTTPException(status_code=404, detail="Sync run not found")
    conflicts = db.scalars(
        select(CanvasSyncConflict)
        .where(CanvasSyncConflict.sync_run_id == run_id)
        .order_by(CanvasSyncConflict.created_at.desc())
    ).all()
    return [_serialize_conflict(conflict) for conflict in conflicts]


@router.get("/sync/conflicts")
def list_sync_conflicts(
    status: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(CanvasSyncConflict)
    if status:
        try:
            parsed = CanvasSyncConflictStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid conflict status") from exc
        query = query.where(CanvasSyncConflict.status == parsed)
    if course_id is not None:
        query = query.where(CanvasSyncConflict.course_id == course_id)
    conflicts = db.scalars(query.order_by(CanvasSyncConflict.created_at.desc()).limit(limit)).all()
    return [_serialize_conflict(conflict) for conflict in conflicts]


@router.post("/sync/conflicts/{conflict_id}/resolve")
def resolve_sync_conflict(
    conflict_id: int,
    payload: CanvasSyncConflictResolutionRequest,
    db: Session = Depends(get_db),
) -> dict:
    conflict = db.get(CanvasSyncConflict, conflict_id)
    if not conflict:
        raise HTTPException(status_code=404, detail="Sync conflict not found")
    if conflict.status != CanvasSyncConflictStatus.pending:
        raise HTTPException(status_code=400, detail="Sync conflict has already been resolved")
    if payload.status == CanvasSyncConflictStatus.pending:
        raise HTTPException(status_code=400, detail="Resolution status must not be pending")

    grade = conflict.grade_entry
    if not grade:
        raise HTTPException(status_code=404, detail="Linked grade entry not found")

    if payload.status == CanvasSyncConflictStatus.accepted_canvas:
        before_snapshot = _grade_snapshot(grade)
        try:
            grade.status = GradeStatus(conflict.canvas_status or GradeStatus.unsubmitted.value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Conflict has invalid Canvas status") from exc
        grade.score = conflict.canvas_score
        grade.letter_grade = None
        grade.completion_status = None
        grade.source = GradeSource.canvas
        grade.snapshot_run_id = conflict.sync_run_id
        db.flush()
        db.add(
            GradeEntryAudit(
                course_id=conflict.course_id,
                assignment_id=conflict.assignment_id,
                student_id=conflict.student_id,
                grade_entry_id=grade.id,
                action="conflict_accept_canvas",
                before_json=before_snapshot,
                after_json=_grade_snapshot(grade),
            )
        )

    conflict.status = payload.status
    conflict.rationale = (payload.rationale or "").strip() or None
    conflict.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conflict)
    return _serialize_conflict(conflict)
