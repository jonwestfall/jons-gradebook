from __future__ import annotations

import mimetypes
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    LLMInstructionTemplate,
    LLMProvider,
    LLMRun,
    LLMWorkbenchJob,
    RubricTemplate,
    StoredDocument,
    StoredDocumentStudentLink,
    StudentProfile,
)
from app.db.session import get_db
from app.schemas.llm import (
    LLMFinalizeRequest,
    LLMFinalFeedbackRequest,
    LLMInstructionTemplateCreate,
    LLMInstructionTemplateUpdate,
    LLMOutputEditRequest,
    LLMPasteOutputRequest,
    LLMPreviewRequest,
)
from app.services.documents import create_or_update_document
from app.services.llm.service import (
    create_instruction_template,
    create_preview_run,
    create_workbench_job,
    duplicate_instruction_template,
    ensure_default_instruction_templates,
    finalize_workbench_job,
    get_run_with_output,
    paste_workbench_output,
    prepare_workbench_job,
    save_final_feedback,
    send_run,
    send_workbench_job_local,
    serialize_instruction_template,
    serialize_workbench_job,
    update_instruction_template,
)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/preview")
def preview_run(payload: LLMPreviewRequest, db: Session = Depends(get_db)) -> dict:
    run = create_preview_run(db, provider=payload.provider, model=payload.model, prompt=payload.prompt)
    detail = get_run_with_output(db, run.id)
    return {
        "run_id": run.id,
        "provider": run.provider.value,
        "model": run.model,
        "status": run.status.value,
        "preview": run.deidentified_preview,
        "deidentify_map": detail["deidentify_map"],
    }


@router.post("/runs/{run_id}/send")
def send_previewed_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        output = send_run(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "output_id": output.id,
        "run_id": output.run_id,
        "message": "LLM output generated and stored",
    }


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(LLMRun).order_by(LLMRun.created_at.desc())).all()
    return [
        {
            "id": run.id,
            "provider": run.provider.value,
            "model": run.model,
            "status": run.status.value,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
        for run in runs
    ]


@router.get("/targets")
def llm_targets(db: Session = Depends(get_db)) -> dict:
    ensure_default_instruction_templates(db)
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    rubrics = db.scalars(
        select(RubricTemplate).where(RubricTemplate.archived_at.is_(None)).order_by(RubricTemplate.name.asc())
    ).all()
    documents = db.scalars(select(StoredDocument).order_by(StoredDocument.updated_at.desc()).limit(500)).all()
    document_ids = [document.id for document in documents]
    links = (
        db.scalars(select(StoredDocumentStudentLink).where(StoredDocumentStudentLink.document_id.in_(document_ids))).all()
        if document_ids
        else []
    )
    links_by_doc: dict[int, list[int]] = {}
    for link in links:
        links_by_doc.setdefault(link.document_id, []).append(link.student_id)

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
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "category": document.category,
                "document_type": document.document_type.value,
                "owner_type": document.owner_type,
                "owner_id": document.owner_id,
                "linked_student_ids": sorted(links_by_doc.get(document.id, [])),
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            }
            for document in documents
        ],
        "rubrics": [
            {
                "id": rubric.id,
                "name": rubric.name,
                "description": rubric.description,
                "max_points": rubric.max_points,
            }
            for rubric in rubrics
        ],
        "providers": [
            {"value": "ollama", "label": "Ollama", "default_model": "llama3.1", "local": True},
            {"value": "openai", "label": "OpenAI", "default_model": "gpt-5-mini", "local": False},
            {"value": "gemini", "label": "Gemini", "default_model": "gemini-1.5-flash", "local": False},
        ],
    }


@router.get("/instructions")
def list_instruction_templates(db: Session = Depends(get_db)) -> list[dict]:
    ensure_default_instruction_templates(db)
    templates = db.scalars(select(LLMInstructionTemplate).order_by(LLMInstructionTemplate.name.asc())).all()
    return [serialize_instruction_template(template) for template in templates]


@router.post("/instructions")
def create_instruction(payload: LLMInstructionTemplateCreate, db: Session = Depends(get_db)) -> dict:
    template = create_instruction_template(db, payload.model_dump())
    return serialize_instruction_template(template)


@router.patch("/instructions/{template_id}")
def update_instruction(template_id: int, payload: LLMInstructionTemplateUpdate, db: Session = Depends(get_db)) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    archived = updates.pop("archived", None)
    if archived is not None:
        updates["archived_at"] = datetime.now(timezone.utc) if archived else None
        if archived:
            updates["is_active"] = False
    try:
        template = update_instruction_template(db, template_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_instruction_template(template)


@router.post("/instructions/{template_id}/duplicate")
def duplicate_instruction(template_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        template = duplicate_instruction_template(db, template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_instruction_template(template)


@router.post("/workbench/jobs")
async def create_job(
    student_id: int = Form(...),
    instruction_template_id: int = Form(...),
    provider: LLMProvider = Form(default=LLMProvider.ollama),
    model: str = Form(default="llama3.1"),
    rubric_id: int | None = Form(default=None),
    source_document_id: int | None = Form(default=None),
    title: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if source_document_id is None and file is None:
        raise HTTPException(status_code=400, detail="Provide an existing source document or upload a file")

    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        filename = file.filename or "student-work.txt"
        mime_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        document = create_or_update_document(
            db,
            owner_type="student",
            owner_id=student_id,
            title=title or filename,
            filename=filename,
            content=content,
            mime_type=mime_type,
            category="Student Work",
            linked_student_ids=[student_id],
        )
        source_document_id = document.id

    try:
        job = create_workbench_job(
            db,
            student_id=student_id,
            source_document_id=int(source_document_id),
            instruction_template_id=instruction_template_id,
            rubric_id=rubric_id,
            provider=provider,
            model=model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_workbench_job(job)


@router.get("/workbench/jobs")
def list_jobs(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(LLMWorkbenchJob).order_by(LLMWorkbenchJob.updated_at.desc(), LLMWorkbenchJob.id.desc()).limit(200)).all()
    return [serialize_workbench_job(job) for job in rows]


@router.get("/workbench/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(LLMWorkbenchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Workbench job not found")
    return serialize_workbench_job(job)


@router.post("/workbench/jobs/{job_id}/prepare")
def prepare_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        job = prepare_workbench_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_workbench_job(job)


@router.post("/workbench/jobs/{job_id}/send-local")
def send_job_local(job_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        output = send_workbench_job_local(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"output_id": output.id, "run_id": output.run_id, "message": "Local LLM output generated and stored"}


@router.post("/workbench/jobs/{job_id}/paste-output")
def paste_output(job_id: int, payload: LLMPasteOutputRequest, db: Session = Depends(get_db)) -> dict:
    try:
        output = paste_workbench_output(db, job_id, payload.output_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"output_id": output.id, "run_id": output.run_id, "message": "Pasted LLM output stored"}


@router.patch("/workbench/jobs/{job_id}/final-feedback")
def update_final_feedback(job_id: int, payload: LLMFinalFeedbackRequest, db: Session = Depends(get_db)) -> dict:
    try:
        job = save_final_feedback(db, job_id, payload.final_feedback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_workbench_job(job)


@router.post("/workbench/jobs/{job_id}/finalize")
def finalize_job(job_id: int, payload: LLMFinalizeRequest, db: Session = Depends(get_db)) -> dict:
    try:
        job = finalize_workbench_job(db, job_id, title=payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_workbench_job(job)


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return get_run_with_output(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/outputs/{output_id}")
def edit_output(output_id: int, payload: LLMOutputEditRequest, db: Session = Depends(get_db)) -> dict:
    try:
        output = update_output_text(db, output_id, payload.edited_text)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "output_id": output.id,
        "run_id": output.run_id,
        "message": "Edited output stored",
    }
