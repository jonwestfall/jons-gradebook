from __future__ import annotations

from collections.abc import Iterable

from dateutil import parser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanvasCourseSelection
from app.services.canvas.client import CanvasReadClient


def _parse_datetime(value: str | None):
    if not value:
        return None
    return parser.isoparse(value)


def _extract_term_dates(course_payload: dict) -> tuple[str | None, object | None, object | None]:
    term_payload = course_payload.get("term") or {}
    term_name = term_payload.get("name")
    term_start = _parse_datetime(term_payload.get("start_at") or course_payload.get("start_at"))
    term_end = _parse_datetime(term_payload.get("end_at") or course_payload.get("end_at"))
    return term_name, term_start, term_end


def discover_and_cache_courses(db: Session) -> list[CanvasCourseSelection]:
    client = CanvasReadClient()
    if not client.configured:
        raise ValueError("Canvas credentials not configured")

    discovered = client.fetch_courses()
    seen_ids: set[str] = set()

    for course_payload in discovered:
        canvas_course_id = str(course_payload["id"])
        seen_ids.add(canvas_course_id)

        term_name, term_start, term_end = _extract_term_dates(course_payload)
        existing = db.scalar(
            select(CanvasCourseSelection).where(CanvasCourseSelection.canvas_course_id == canvas_course_id)
        )

        if not existing:
            existing = CanvasCourseSelection(
                canvas_course_id=canvas_course_id,
                name=course_payload.get("name", "Untitled Course"),
                course_code=course_payload.get("course_code"),
                term_name=term_name,
                term_start_at=term_start,
                term_end_at=term_end,
                is_selected=False,
            )
            db.add(existing)
        else:
            existing.name = course_payload.get("name", existing.name)
            existing.course_code = course_payload.get("course_code", existing.course_code)
            existing.term_name = term_name or existing.term_name
            existing.term_start_at = term_start
            existing.term_end_at = term_end

    db.commit()

    courses = db.scalars(select(CanvasCourseSelection).order_by(CanvasCourseSelection.name.asc())).all()
    return list(courses)


def list_course_selections(db: Session) -> list[CanvasCourseSelection]:
    return list(db.scalars(select(CanvasCourseSelection).order_by(CanvasCourseSelection.name.asc())).all())


def selected_course_ids(db: Session) -> list[str]:
    rows = db.scalars(
        select(CanvasCourseSelection.canvas_course_id).where(CanvasCourseSelection.is_selected.is_(True))
    ).all()
    return [str(row) for row in rows]


def set_selected_courses(db: Session, canvas_course_ids: Iterable[str], mode: str = "replace") -> list[CanvasCourseSelection]:
    desired = {str(course_id) for course_id in canvas_course_ids}
    rows = db.scalars(select(CanvasCourseSelection)).all()
    by_id = {row.canvas_course_id: row for row in rows}

    missing = sorted(desired - set(by_id.keys()))
    if missing:
        raise ValueError(
            "Unknown Canvas course IDs in selection: " + ", ".join(missing) + ". Discover courses first."
        )

    if mode not in {"replace", "add"}:
        raise ValueError("Selection mode must be 'replace' or 'add'")

    for row in rows:
        if mode == "replace":
            row.is_selected = row.canvas_course_id in desired
        elif mode == "add" and row.canvas_course_id in desired:
            row.is_selected = True

    db.commit()
    return list_course_selections(db)
