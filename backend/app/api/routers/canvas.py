from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanvasSyncRun
from app.db.session import get_db
from app.schemas.canvas import (
    CanvasCourseSelectionUpdateRequest,
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
    }
