from __future__ import annotations

import mimetypes
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InteractionLog, InteractionType, StoredDocument
from app.db.session import get_db
from app.services.documents import create_or_update_document, get_document_text, read_document_file

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
def list_documents(db: Session = Depends(get_db)) -> list[dict]:
    documents = db.scalars(select(StoredDocument).order_by(StoredDocument.updated_at.desc())).all()
    return [
        {
            "id": document.id,
            "title": document.title,
            "owner_type": document.owner_type,
            "owner_id": document.owner_id,
            "document_type": document.document_type.value,
            "current_version": document.current_version,
        }
        for document in documents
    ]


@router.post("/upload")
async def upload_document(
    owner_type: str = Form(...),
    owner_id: int = Form(...),
    title: str = Form(...),
    document_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"

    try:
        document = create_or_update_document(
            db,
            owner_type=owner_type,
            owner_id=owner_id,
            title=title,
            document_id=document_id,
            filename=file.filename or "upload.bin",
            content=content,
            mime_type=mime_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    interaction = InteractionLog(
        student_profile_id=owner_id if owner_type == "student" else None,
        advisee_id=owner_id if owner_type == "advisee" else None,
        interaction_type=InteractionType.file_upload,
        occurred_at=datetime.now(timezone.utc),
        summary=f"Uploaded document: {document.title}",
        notes=f"Document ID {document.id} version {document.current_version}",
        metadata_json={
            "document_id": document.id,
            "version": document.current_version,
            "owner_type": owner_type,
            "filename": file.filename,
        },
    )
    db.add(interaction)
    db.commit()

    return {
        "id": document.id,
        "title": document.title,
        "owner_type": document.owner_type,
        "owner_id": document.owner_id,
        "current_version": document.current_version,
    }


@router.get("/{document_id}/text")
def document_text(document_id: int, version: int | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        text = get_document_text(db, document_id=document_id, version_number=version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"document_id": document_id, "version": version, "text": text}


@router.get("/{document_id}/download")
def download_document(document_id: int, version: int | None = None, db: Session = Depends(get_db)) -> StreamingResponse:
    document = db.get(StoredDocument, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        raw_bytes = read_document_file(db, document_id=document_id, version_number=version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ext = {
        "pdf": ".pdf",
        "docx": ".docx",
        "txt": ".txt",
    }.get(document.document_type.value, ".bin")

    filename = f"document-{document_id}-v{version or document.current_version}{ext}"
    media_type = mimetypes.guess_type(Path(filename).name)[0] or "application/octet-stream"

    return StreamingResponse(
        iter([raw_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
