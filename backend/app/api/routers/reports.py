from __future__ import annotations

import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Assignment, ReportRun, ReportTemplate, RubricTemplate, StudentProfile
from app.db.session import get_db
from app.schemas.reports import (
    BulkStudentReportRequest,
    ReportTemplateCreate,
    ReportTemplateUpdate,
    StudentReportRequest,
)
from app.services.documents import create_or_update_document
from app.services.reports import (
    ensure_default_report_templates,
    generate_student_report,
    normalize_report_config,
    save_template_logo,
    serialize_report_template,
    set_default_template,
    _latest_logo_asset,
    _student_summary,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:50] or "report"


def _report_basename(
    student_id: int,
    include_all_rubrics: bool,
    rubric_id: int | None,
    assignment_id: int | None,
    template: ReportTemplate | None = None,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scope = "all-rubrics"
    if not include_all_rubrics:
        parts: list[str] = []
        if rubric_id is not None:
            parts.append(f"rubric-{rubric_id}")
        if assignment_id is not None:
            parts.append(f"assignment-{assignment_id}")
        scope = "-".join(parts) if parts else "filtered"
    template_slug = _slug(template.name) if template else "student-report"
    return f"student-{student_id}-{template_slug}-{scope}-{timestamp}"


def _download_urls(student_id: int, pdf_path: str, png_path: str) -> dict[str, str]:
    settings = get_settings()
    pdf_name = Path(pdf_path).name
    png_name = Path(png_path).name
    return {
        "pdf_url": f"{settings.api_v1_prefix}/reports/files/{student_id}/{pdf_name}",
        "png_url": f"{settings.api_v1_prefix}/reports/files/{student_id}/{png_name}",
    }


def _get_template(db: Session, template_id: int | None) -> ReportTemplate:
    ensure_default_report_templates(db)
    if template_id is not None:
        template = db.get(ReportTemplate, template_id)
        if not template or template.archived_at is not None:
            raise HTTPException(status_code=404, detail="Report template not found")
        return template

    template = db.scalar(
        select(ReportTemplate)
        .where(
            ReportTemplate.report_type == "student",
            ReportTemplate.is_default.is_(True),
            ReportTemplate.archived_at.is_(None),
        )
        .order_by(ReportTemplate.id.asc())
    )
    if template:
        return template
    fallback = db.scalar(
        select(ReportTemplate)
        .where(ReportTemplate.report_type == "student", ReportTemplate.archived_at.is_(None))
        .order_by(ReportTemplate.id.asc())
    )
    if not fallback:
        raise HTTPException(status_code=404, detail="No report template available")
    return fallback


def _create_report_documents(db: Session, student_id: int, template: ReportTemplate, pdf_path: str, png_path: str) -> tuple[int, int]:
    student = db.get(StudentProfile, student_id)
    student_name = f"{student.first_name} {student.last_name}".strip() if student else f"Student {student_id}"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf_document = create_or_update_document(
        db,
        owner_type="student",
        owner_id=student_id,
        title=f"{template.name} PDF - {student_name} - {stamp}",
        category="Report",
        filename=Path(pdf_path).name,
        content=Path(pdf_path).read_bytes(),
        mime_type="application/pdf",
        linked_student_ids=[student_id],
    )
    png_document = create_or_update_document(
        db,
        owner_type="student",
        owner_id=student_id,
        title=f"{template.name} PNG - {student_name} - {stamp}",
        category="Report",
        filename=Path(png_path).name,
        content=Path(png_path).read_bytes(),
        mime_type="image/png",
        linked_student_ids=[student_id],
    )
    return pdf_document.id, png_document.id


def _serialize_run(run: ReportRun) -> dict:
    urls = _download_urls(run.student_id, run.pdf_path, run.png_path)
    return {
        "id": run.id,
        "student_id": run.student_id,
        "student_name": f"{run.student.first_name} {run.student.last_name}".strip() if run.student else f"Student {run.student_id}",
        "template_id": run.template_id,
        "template_name": run.template.name if run.template else "Deleted template",
        "filters": run.filters_json,
        "pdf_url": urls["pdf_url"],
        "png_url": urls["png_url"],
        "pdf_document_id": run.pdf_document_id,
        "png_document_id": run.png_document_id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


@router.get("/targets")
def list_report_targets(db: Session = Depends(get_db)) -> dict:
    ensure_default_report_templates(db)
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    rubrics = db.scalars(
        select(RubricTemplate).where(RubricTemplate.archived_at.is_(None)).order_by(RubricTemplate.name.asc())
    ).all()
    assignments = db.scalars(select(Assignment).order_by(Assignment.title.asc())).all()
    templates = db.scalars(
        select(ReportTemplate)
        .where(ReportTemplate.report_type == "student", ReportTemplate.archived_at.is_(None))
        .order_by(ReportTemplate.is_default.desc(), ReportTemplate.name.asc())
    ).all()

    return {
        "students": [
            {
                "id": student.id,
                "name": f"{student.first_name} {student.last_name}".strip(),
                "email": student.email,
                "student_number": student.student_number,
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
        "templates": [serialize_report_template(template) for template in templates],
    }


@router.get("/templates")
def list_report_templates(include_archived: bool = False, db: Session = Depends(get_db)) -> list[dict]:
    ensure_default_report_templates(db)
    query = select(ReportTemplate).where(ReportTemplate.report_type == "student")
    if not include_archived:
        query = query.where(ReportTemplate.archived_at.is_(None))
    templates = db.scalars(query.order_by(ReportTemplate.is_default.desc(), ReportTemplate.name.asc())).all()
    return [serialize_report_template(template) for template in templates]


@router.post("/templates")
def create_report_template(payload: ReportTemplateCreate, db: Session = Depends(get_db)) -> dict:
    ensure_default_report_templates(db)
    template = ReportTemplate(
        name=payload.name.strip(),
        description=payload.description,
        report_type="student",
        is_active=True,
        is_default=payload.is_default,
        config_json=normalize_report_config(payload.config_json),
    )
    db.add(template)
    db.flush()
    if payload.is_default:
        set_default_template(db, template)
    db.commit()
    db.refresh(template)
    return serialize_report_template(template)


@router.get("/templates/{template_id}")
def get_report_template(template_id: int, db: Session = Depends(get_db)) -> dict:
    ensure_default_report_templates(db)
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    return serialize_report_template(template)


@router.patch("/templates/{template_id}")
def update_report_template(template_id: int, payload: ReportTemplateUpdate, db: Session = Depends(get_db)) -> dict:
    ensure_default_report_templates(db)
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")

    if payload.name is not None:
        template.name = payload.name.strip()
    if payload.description is not None:
        template.description = payload.description
    if payload.config_json is not None:
        template.config_json = normalize_report_config(payload.config_json)
    if payload.is_active is not None:
        template.is_active = payload.is_active
    if payload.archived is not None:
        template.archived_at = datetime.now(timezone.utc) if payload.archived else None
        if payload.archived:
            template.is_default = False
    if payload.is_default is not None:
        if payload.is_default:
            template.archived_at = None
            template.is_active = True
            set_default_template(db, template)
        else:
            template.is_default = False

    db.commit()
    db.refresh(template)
    return serialize_report_template(template)


@router.post("/templates/{template_id}/duplicate")
def duplicate_report_template(template_id: int, db: Session = Depends(get_db)) -> dict:
    ensure_default_report_templates(db)
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    duplicate = ReportTemplate(
        name=f"{template.name} Copy",
        description=template.description,
        report_type=template.report_type,
        is_active=True,
        is_default=False,
        config_json=normalize_report_config(template.config_json),
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return serialize_report_template(duplicate)


@router.post("/templates/{template_id}/assets/logo")
async def upload_report_template_logo(
    template_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    content = await file.read()
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    try:
        save_template_logo(db, template, file.filename or "logo", content, mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(template)
    return serialize_report_template(template)


@router.get("/templates/{template_id}/assets/logo")
def download_report_template_logo(template_id: int, db: Session = Depends(get_db)) -> FileResponse:
    template = db.get(ReportTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Report template not found")
    logo = _latest_logo_asset(template)
    if not logo or not Path(logo.file_path).exists():
        raise HTTPException(status_code=404, detail="Template logo not found")
    return FileResponse(path=logo.file_path, media_type=logo.mime_type, filename=logo.original_filename)


@router.get("/students/{student_id}/preview")
def preview_student_report(
    student_id: int,
    template_id: int | None = None,
    include_all_rubrics: bool = True,
    rubric_id: int | None = None,
    assignment_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    template = _get_template(db, template_id)
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
        "student_number": summary["student"].student_number,
        "template": serialize_report_template(template),
        "template_config": normalize_report_config(template.config_json),
        "courses": summary["courses"],
        "grade_overview": summary["grade_overview"],
        "attendance": summary["attendance"],
        "rubric_scope": summary["rubric_scope"],
        "rubric_evaluations": summary["rubric_evaluations"],
        "recent_interactions": summary["recent_interactions"],
        "advising_meetings": summary["advising_meetings"],
        "tasks": summary["tasks"],
        "linked_documents": summary["linked_documents"],
    }


@router.post("/students/{student_id}")
def create_student_report(
    student_id: int,
    payload: StudentReportRequest,
    db: Session = Depends(get_db),
) -> dict:
    template = _get_template(db, payload.template_id)
    if payload.rubric_id is not None and not db.get(RubricTemplate, payload.rubric_id):
        raise HTTPException(status_code=404, detail="Rubric not found")
    if payload.assignment_id is not None and not db.get(Assignment, payload.assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")

    basename = _report_basename(
        student_id,
        payload.include_all_rubrics,
        payload.rubric_id,
        payload.assignment_id,
        template,
    )

    try:
        paths = generate_student_report(
            db,
            student_id,
            basename=basename,
            include_all_rubrics=payload.include_all_rubrics,
            rubric_id=payload.rubric_id,
            assignment_id=payload.assignment_id,
            template=template,
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

    pdf_document_id, png_document_id = _create_report_documents(db, student_id, template, paths["pdf_path"], paths["png_path"])
    run = ReportRun(
        template_id=template.id,
        student_id=student_id,
        report_type="student",
        filters_json={
            "include_all_rubrics": payload.include_all_rubrics,
            "rubric_id": payload.rubric_id,
            "assignment_id": payload.assignment_id,
        },
        pdf_path=paths["pdf_path"],
        png_path=paths["png_path"],
        pdf_document_id=pdf_document_id,
        png_document_id=png_document_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    urls = _download_urls(student_id, paths["pdf_path"], paths["png_path"])

    return {
        "run_id": run.id,
        "student_id": student_id,
        "template": serialize_report_template(template),
        "pdf_path": paths["pdf_path"],
        "png_path": paths["png_path"],
        "pdf_url": urls["pdf_url"],
        "png_url": urls["png_url"],
        "pdf_document_id": pdf_document_id,
        "png_document_id": png_document_id,
        "rubric_scope": summary["rubric_scope"],
        "rubric_evaluation_count": len(summary["rubric_evaluations"]),
        "interaction_count": len(summary["recent_interactions"]),
    }


@router.post("/students/bulk")
def create_bulk_student_reports(payload: BulkStudentReportRequest, db: Session = Depends(get_db)) -> dict:
    template = _get_template(db, payload.template_id)
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    artifacts: list[dict] = []

    for student in students:
        basename = _report_basename(
            student.id,
            payload.include_all_rubrics,
            payload.rubric_id,
            payload.assignment_id,
            template,
        )
        paths = generate_student_report(
            db,
            student.id,
            basename=basename,
            include_all_rubrics=payload.include_all_rubrics,
            rubric_id=payload.rubric_id,
            assignment_id=payload.assignment_id,
            template=template,
        )
        pdf_document_id, png_document_id = _create_report_documents(db, student.id, template, paths["pdf_path"], paths["png_path"])
        run = ReportRun(
            template_id=template.id,
            student_id=student.id,
            report_type="student",
            filters_json={
                "include_all_rubrics": payload.include_all_rubrics,
                "rubric_id": payload.rubric_id,
                "assignment_id": payload.assignment_id,
            },
            pdf_path=paths["pdf_path"],
            png_path=paths["png_path"],
            pdf_document_id=pdf_document_id,
            png_document_id=png_document_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        urls = _download_urls(student.id, paths["pdf_path"], paths["png_path"])
        artifacts.append(
            {
                "run_id": run.id,
                "student_id": student.id,
                "student_name": f"{student.first_name} {student.last_name}".strip(),
                "pdf_url": urls["pdf_url"],
                "png_url": urls["png_url"],
                "pdf_document_id": pdf_document_id,
                "png_document_id": png_document_id,
            }
        )

    return {
        "created_count": len(artifacts),
        "template": serialize_report_template(template),
        "artifacts": artifacts,
    }


@router.get("/runs")
def list_report_runs(limit: int = Query(default=50, ge=1, le=250), db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(ReportRun).order_by(desc(ReportRun.created_at), desc(ReportRun.id)).limit(limit)).all()
    return [_serialize_run(run) for run in runs]


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
