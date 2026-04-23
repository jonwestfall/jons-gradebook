from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    Advisee,
    AppOption,
    DocumentType,
    InteractionLog,
    InteractionType,
    StoredDocument,
    StoredDocumentStudentLink,
    StoredDocumentVersion,
    StudentProfile,
)
from app.db.session import get_db
from app.services.documents import (
    create_or_update_document,
    get_document_text,
    read_document_file,
    set_document_student_links,
)

router = APIRouter(prefix="/documents", tags=["documents"])
DEFAULT_DOCUMENT_CATEGORIES = ["Record", "Assignment", "Note", "Other"]


def _parse_student_ids(value: str | None) -> list[int]:
    if not value:
        return []
    parsed: list[int] = []
    for raw in value.split(","):
        token = raw.strip()
        if not token:
            continue
        try:
            number = int(token)
        except ValueError:
            continue
        if number > 0:
            parsed.append(number)
    return sorted(set(parsed))


def _document_payload(document: StoredDocument, links_by_doc: dict[int, list[dict]], latest_version_by_doc: dict[int, StoredDocumentVersion]) -> dict:
    latest_version = latest_version_by_doc.get(document.id)
    return {
        "id": document.id,
        "title": document.title,
        "category": document.category,
        "owner_type": document.owner_type,
        "owner_id": document.owner_id,
        "document_type": document.document_type.value,
        "current_version": document.current_version,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "linked_students": links_by_doc.get(document.id, []),
        "latest_version": {
            "version_number": latest_version.version_number,
            "original_filename": latest_version.original_filename,
            "mime_type": latest_version.mime_type,
            "size_bytes": latest_version.size_bytes,
            "checksum_sha256": latest_version.checksum_sha256,
            "updated_at": latest_version.updated_at.isoformat() if latest_version.updated_at else None,
        }
        if latest_version
        else None,
    }


@router.get("/targets")
def document_targets(db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(StudentProfile).order_by(StudentProfile.last_name.asc(), StudentProfile.first_name.asc())).all()
    advisees = db.scalars(select(Advisee).order_by(Advisee.last_name.asc(), Advisee.first_name.asc())).all()
    category_option = db.scalar(select(AppOption).where(AppOption.key == "document_categories"))
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
        "advisees": [
            {
                "id": advisee.id,
                "name": f"{advisee.first_name} {advisee.last_name}".strip(),
                "student_profile_id": advisee.student_profile_id,
            }
            for advisee in advisees
        ],
        "document_categories": category_option.value_json if category_option else DEFAULT_DOCUMENT_CATEGORIES,
    }


@router.get("/")
def list_documents(
    search: str | None = Query(default=None),
    student_id: int | None = Query(default=None),
    document_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    person_name: str | None = Query(default=None),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(StoredDocument)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(StoredDocument.title.ilike(pattern))

    if document_type:
        try:
            parsed_type = DocumentType(document_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid document_type") from exc
        query = query.where(StoredDocument.document_type == parsed_type)

    if student_id is not None:
        query = query.join(
            StoredDocumentStudentLink,
            StoredDocumentStudentLink.document_id == StoredDocument.id,
        ).where(StoredDocumentStudentLink.student_id == student_id)

    if category:
        query = query.where(StoredDocument.category == category)

    sort_map = {
        "updated_at": StoredDocument.updated_at,
        "created_at": StoredDocument.created_at,
        "title": StoredDocument.title,
        "document_type": StoredDocument.document_type,
        "current_version": StoredDocument.current_version,
    }
    field = sort_map.get(sort_by, StoredDocument.updated_at)
    direction = asc if sort_order.lower() == "asc" else desc
    documents = db.scalars(query.order_by(direction(field), desc(StoredDocument.id)).limit(limit)).all()

    if not documents:
        return []

    document_ids = [document.id for document in documents]

    links = db.scalars(
        select(StoredDocumentStudentLink)
        .where(StoredDocumentStudentLink.document_id.in_(document_ids))
        .order_by(StoredDocumentStudentLink.document_id.asc())
    ).all()
    student_ids = {link.student_id for link in links}
    students = (
        db.scalars(select(StudentProfile).where(StudentProfile.id.in_(student_ids))).all() if student_ids else []
    )
    student_map = {
        student.id: {
            "id": student.id,
            "name": f"{student.first_name} {student.last_name}".strip(),
            "email": student.email,
        }
        for student in students
    }

    owner_student_ids = {document.owner_id for document in documents if document.owner_type == "student"}
    owner_advisee_ids = {document.owner_id for document in documents if document.owner_type == "advisee"}
    owner_student_map = {
        student.id: f"{student.first_name} {student.last_name}".strip()
        for student in (
            db.scalars(select(StudentProfile).where(StudentProfile.id.in_(owner_student_ids))).all() if owner_student_ids else []
        )
    }
    owner_advisee_map = {
        advisee.id: f"{advisee.first_name} {advisee.last_name}".strip()
        for advisee in (db.scalars(select(Advisee).where(Advisee.id.in_(owner_advisee_ids))).all() if owner_advisee_ids else [])
    }

    links_by_doc: dict[int, list[dict]] = {}
    for link in links:
        links_by_doc.setdefault(link.document_id, []).append(student_map.get(link.student_id, {"id": link.student_id, "name": f"Student {link.student_id}", "email": None}))

    versions = db.scalars(
        select(StoredDocumentVersion).where(StoredDocumentVersion.document_id.in_(document_ids))
    ).all()
    latest_version_by_doc: dict[int, StoredDocumentVersion] = {}
    for version in versions:
        current = latest_version_by_doc.get(version.document_id)
        if current is None or version.version_number > current.version_number:
            latest_version_by_doc[version.document_id] = version

    payload = []
    for document in documents:
        item = _document_payload(document, links_by_doc, latest_version_by_doc)
        if document.owner_type == "student":
            item["owner_name"] = owner_student_map.get(document.owner_id)
        elif document.owner_type == "advisee":
            item["owner_name"] = owner_advisee_map.get(document.owner_id)
        else:
            item["owner_name"] = None
        payload.append(item)

    if person_name:
        query_name = person_name.strip().lower()
        payload = [
            item
            for item in payload
            if (
                (item.get("owner_name") and query_name in str(item.get("owner_name")).lower())
                or any(query_name in student.get("name", "").lower() for student in item.get("linked_students", []))
            )
        ]

    return payload


@router.get("/by-student/{student_id}")
def list_documents_for_student(student_id: int, db: Session = Depends(get_db)) -> list[dict]:
    return list_documents(student_id=student_id, limit=500, db=db)


@router.post("/upload")
async def upload_document(
    owner_type: str = Form(...),
    owner_id: int = Form(...),
    title: str = Form(...),
    category: str | None = Form(default=None),
    linked_student_ids: str | None = Form(default=None),
    document_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    student_ids = _parse_student_ids(linked_student_ids)

    try:
        document = create_or_update_document(
            db,
            owner_type=owner_type,
            owner_id=owner_id,
            title=title,
            category=category,
            document_id=document_id,
            filename=file.filename or "upload.bin",
            content=content,
            mime_type=mime_type,
            linked_student_ids=student_ids,
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
            "linked_student_ids": student_ids,
        },
    )
    db.add(interaction)
    db.commit()

    links = db.scalars(
        select(StoredDocumentStudentLink).where(StoredDocumentStudentLink.document_id == document.id)
    ).all()

    return {
        "id": document.id,
        "title": document.title,
        "category": document.category,
        "owner_type": document.owner_type,
        "owner_id": document.owner_id,
        "current_version": document.current_version,
        "linked_student_ids": sorted({link.student_id for link in links}),
    }


@router.post("/{document_id}/link-students")
def link_document_students(document_id: int, payload: dict, db: Session = Depends(get_db)) -> dict:
    raw_ids = payload.get("student_ids", [])
    if not isinstance(raw_ids, list):
        raise HTTPException(status_code=400, detail="student_ids must be a list")

    try:
        ids = [int(item) for item in raw_ids]
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="student_ids must contain integers") from exc

    try:
        linked = set_document_student_links(db, document_id=document_id, student_ids=ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "document_id": document_id,
        "student_ids": linked,
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

    version_row = db.scalar(
        select(StoredDocumentVersion).where(
            StoredDocumentVersion.document_id == document_id,
            StoredDocumentVersion.version_number == (version or document.current_version),
        )
    )
    if not version_row:
        raise HTTPException(status_code=404, detail="Version not found")

    try:
        raw_bytes = read_document_file(db, document_id=document_id, version_number=version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ext = {
        "pdf": ".pdf",
        "docx": ".docx",
        "txt": ".txt",
    }.get(document.document_type.value, Path(version_row.original_filename).suffix or ".bin")

    filename = f"{document.title.strip() or 'document'}-v{version or document.current_version}{ext}"
    media_type = version_row.mime_type or mimetypes.guess_type(Path(filename).name)[0] or "application/octet-stream"

    return StreamingResponse(
        iter([raw_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{Path(filename).name}"'},
    )
