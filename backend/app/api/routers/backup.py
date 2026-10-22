from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import BackupArtifact
from app.db.session import get_db
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup import (
    BackupCompatibilityError,
    BackupError,
    create_encrypted_backup,
    import_backup_file,
    inspect_backup,
    inspect_current_state,
    restore_from_backup_artifact,
    restore_preflight,
)

router = APIRouter(prefix="/backup", tags=["backup"])


def _serialize_artifact(artifact: BackupArtifact) -> dict:
    return {
        "id": artifact.id,
        "backup_path": artifact.backup_path,
        "checksum_sha256": artifact.checksum_sha256,
        "encrypted": artifact.encrypted,
        "created_at": artifact.created_at.isoformat(),
        "note": artifact.note,
    }


def _get_artifact(db: Session, backup_id: int) -> BackupArtifact:
    artifact = db.get(BackupArtifact, backup_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Backup not found")
    return artifact


def _backup_http_error(exc: BackupError) -> HTTPException:
    status_code = 409 if isinstance(exc, BackupCompatibilityError) else 422
    return HTTPException(status_code=status_code, detail=str(exc))


@router.post("/")
def create_backup(payload: BackupCreateRequest, db: Session = Depends(get_db)) -> dict:
    artifact = create_encrypted_backup(db, note=payload.note)
    return _serialize_artifact(artifact)


@router.get("/")
def list_backups(db: Session = Depends(get_db)) -> list[dict]:
    backups = db.scalars(select(BackupArtifact).order_by(BackupArtifact.created_at.desc(), BackupArtifact.id.desc())).all()
    return [_serialize_artifact(backup) for backup in backups]


@router.post("/import")
async def import_backup(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    content = await file.read()
    try:
        artifact = import_backup_file(db, content, original_filename=file.filename)
    except BackupError as exc:
        raise _backup_http_error(exc) from exc
    return _serialize_artifact(artifact)


@router.get("/{backup_id}")
def get_backup(backup_id: int, db: Session = Depends(get_db)) -> dict:
    artifact = _get_artifact(db, backup_id)
    try:
        details = inspect_backup(artifact)
    except BackupError as exc:
        raise _backup_http_error(exc) from exc
    return {**_serialize_artifact(artifact), **details}


@router.get("/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db)) -> FileResponse:
    artifact = _get_artifact(db, backup_id)
    path = Path(artifact.backup_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Backup file is missing from disk")
    return FileResponse(path=str(path), media_type="application/octet-stream", filename=path.name)


@router.get("/{backup_id}/preflight")
def get_backup_restore_preflight(backup_id: int, db: Session = Depends(get_db)) -> dict:
    artifact = _get_artifact(db, backup_id)
    try:
        preflight = restore_preflight(db, artifact)
    except BackupError as exc:
        raise _backup_http_error(exc) from exc

    payload = preflight["payload"]
    backup_tables = {
        table_name: len(rows) if isinstance(rows, list) else 0 for table_name, rows in payload["tables"].items()
    }
    backup_file_count = len(payload.get("files") or [])
    current_details = inspect_current_state(db)
    current_tables = current_details.get("table_counts", {})
    all_table_names = sorted(set(backup_tables.keys()) | set(current_tables.keys()))
    table_deltas = [
        {
            "table": table_name,
            "current_rows": int(current_tables.get(table_name, 0)),
            "backup_rows": int(backup_tables.get(table_name, 0)),
            "delta_rows": int(backup_tables.get(table_name, 0)) - int(current_tables.get(table_name, 0)),
        }
        for table_name in all_table_names
    ]

    return {
        "backup_id": artifact.id,
        "backup_generated_at": payload.get("generated_at"),
        "backup_alembic_revision": preflight["backup_alembic_revision"],
        "current_alembic_revision": preflight["current_alembic_revision"],
        "can_restore": preflight["can_restore"],
        "warnings": preflight["warnings"],
        "current_file_count": int(current_details.get("file_count", 0)),
        "backup_file_count": backup_file_count,
        "file_delta": backup_file_count - int(current_details.get("file_count", 0)),
        "table_deltas": table_deltas,
    }


@router.post("/restore")
def restore_backup(payload: BackupRestoreRequest, db: Session = Depends(get_db)) -> dict:
    artifact = _get_artifact(db, payload.backup_id)
    backup_path = artifact.backup_path
    try:
        restored = restore_from_backup_artifact(db, artifact, create_safety_backup=payload.create_safety_backup)
    except BackupError as exc:
        raise _backup_http_error(exc) from exc
    except SQLAlchemyError as exc:
        # The restore runs in one transaction and swaps files only at the end, so nothing changed.
        reason = str(getattr(exc, "orig", None) or exc).splitlines()[0]
        raise HTTPException(
            status_code=422, detail=f"Restore failed and was rolled back; no data or files were changed. {reason}"
        ) from exc
    return {"backup_path": backup_path, **restored}
