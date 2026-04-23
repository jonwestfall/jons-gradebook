from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Assignment, RubricTemplate, StudentProfile
from app.db.session import get_db
from app.schemas.reports import BulkStudentReportRequest, StudentReportRequest
from app.services.reports import _student_summary, generate_student_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_basename(student_id: int, include_all_rubrics: bool, rubric_id: int | None, assignment_id: int | None) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scope = "all-rubrics"
    if not include_all_rubrics:
        parts: list[str] = []
        if rubric_id is not None:
            parts.append(f"rubric-{rubric_id}")
        if assignment_id is not None:
            parts.append(f"assignment-{assignment_id}")
        scope = "-".join(parts) if parts else "filtered"
    return f"student-{student_id}-{scope}-{timestamp}"


def _download_urls(student_id: int, pdf_path: str, png_path: str) -> dict[str, str]:
    settings = get_settings()
    pdf_name = Path(pdf_path).name
    png_name = Path(png_path).name
    return {
        "pdf_url": f"{settings.api_v1_prefix}/reports/files/{student_id}/{pdf_name}",
        "png_url": f"{settings.api_v1_prefix}/reports/files/{student_id}/{png_name}",
    }


@router.get("/targets")
def list_report_targets(db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    rubrics = db.scalars(select(RubricTemplate).order_by(RubricTemplate.name.asc())).all()
    assignments = db.scalars(select(Assignment).order_by(Assignment.title.asc())).all()

    return {
        "students": [
            {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "email": student.email,
            }
            for student in students
        ],
        "rubrics": [
            {
                "id": rubric.id,
                "name": rubric.name,
            }
            for rubric in rubrics
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


@router.get("/students/{student_id}/preview")
def preview_student_report(
    student_id: int,
    include_all_rubrics: bool = True,
    rubric_id: int | None = None,
    assignment_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    try:
        summary = _student_summary(
            db,
            student_id,
            include_all_rubrics=include_all_rubrics,
            rubric_id=rubric_id,
            assignment_id=assignment_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "student_id": student_id,
        "student_name": f"{summary['student'].first_name} {summary['student'].last_name}".strip(),
        "courses": summary["courses"],
        "grade_overview": summary["grade_overview"],
        "attendance": summary["attendance"],
        "rubric_scope": summary["rubric_scope"],
        "rubric_evaluations": summary["rubric_evaluations"],
        "recent_interactions": summary["recent_interactions"],
    }


@router.post("/students/{student_id}")
def create_student_report(
    student_id: int,
    payload: StudentReportRequest,
    db: Session = Depends(get_db),
) -> dict:
    if payload.rubric_id is not None and not db.get(RubricTemplate, payload.rubric_id):
        raise HTTPException(status_code=404, detail="Rubric not found")
    if payload.assignment_id is not None and not db.get(Assignment, payload.assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")

    basename = _report_basename(
        student_id,
        payload.include_all_rubrics,
        payload.rubric_id,
        payload.assignment_id,
    )

    try:
        paths = generate_student_report(
            db,
            student_id,
            basename=basename,
            include_all_rubrics=payload.include_all_rubrics,
            rubric_id=payload.rubric_id,
            assignment_id=payload.assignment_id,
        )
        summary = _student_summary(
            db,
            student_id,
            include_all_rubrics=payload.include_all_rubrics,
            rubric_id=payload.rubric_id,
            assignment_id=payload.assignment_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    urls = _download_urls(student_id, paths["pdf_path"], paths["png_path"])

    return {
        "student_id": student_id,
        "pdf_path": paths["pdf_path"],
        "png_path": paths["png_path"],
        "pdf_url": urls["pdf_url"],
        "png_url": urls["png_url"],
        "rubric_scope": summary["rubric_scope"],
        "rubric_evaluation_count": len(summary["rubric_evaluations"]),
        "interaction_count": len(summary["recent_interactions"]),
    }


@router.post("/students/bulk")
def create_bulk_student_reports(payload: BulkStudentReportRequest, db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    artifacts: list[dict] = []

    for student in students:
        basename = _report_basename(
            student.id,
            payload.include_all_rubrics,
            payload.rubric_id,
            payload.assignment_id,
        )
        paths = generate_student_report(
            db,
            student.id,
            basename=basename,
            include_all_rubrics=payload.include_all_rubrics,
            rubric_id=payload.rubric_id,
            assignment_id=payload.assignment_id,
        )
        urls = _download_urls(student.id, paths["pdf_path"], paths["png_path"])
        artifacts.append(
            {
                "student_id": student.id,
                "student_name": f"{student.first_name} {student.last_name}".strip(),
                "pdf_url": urls["pdf_url"],
                "png_url": urls["png_url"],
            }
        )

    return {
        "created_count": len(artifacts),
        "artifacts": artifacts,
    }


@router.get("/files/{student_id}/{filename}")
def download_report_file(student_id: int, filename: str) -> FileResponse:
    settings = get_settings()
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    student_dir = (Path(settings.storage_root) / "reports" / str(student_id)).resolve()
    file_path = (student_dir / safe_name).resolve()
    if student_dir not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    if file_path.suffix.lower() == ".pdf":
        media_type = "application/pdf"
    elif file_path.suffix.lower() == ".png":
        media_type = "image/png"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return FileResponse(path=str(file_path), media_type=media_type, filename=file_path.name)
