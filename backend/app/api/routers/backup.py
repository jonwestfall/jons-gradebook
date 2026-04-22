from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BackupArtifact
from app.db.session import get_db
from app.schemas.backup import BackupCreateRequest, BackupRestoreRequest
from app.services.backup import create_encrypted_backup, inspect_backup, restore_from_backup_artifact

router = APIRouter(prefix="/backup", tags=["backup"])


@router.post("/")
def create_backup(payload: BackupCreateRequest, db: Session = Depends(get_db)) -> dict:
    artifact = create_encrypted_backup(db, note=payload.note)
    return {
        "id": artifact.id,
        "backup_path": artifact.backup_path,
        "checksum_sha256": artifact.checksum_sha256,
        "encrypted": artifact.encrypted,
        "created_at": artifact.created_at.isoformat(),
    }


@router.get("/")
def list_backups(db: Session = Depends(get_db)) -> list[dict]:
    backups = db.scalars(select(BackupArtifact).order_by(BackupArtifact.created_at.desc())).all()
    return [
        {
            "id": backup.id,
            "backup_path": backup.backup_path,
            "checksum_sha256": backup.checksum_sha256,
            "encrypted": backup.encrypted,
            "created_at": backup.created_at.isoformat(),
            "note": backup.note,
        }
        for backup in backups
    ]


@router.get("/{backup_id}")
def get_backup(backup_id: int, db: Session = Depends(get_db)) -> dict:
    artifact = db.get(BackupArtifact, backup_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Backup not found")
    details = inspect_backup(artifact)
    return {
        "id": artifact.id,
        "backup_path": artifact.backup_path,
        "checksum_sha256": artifact.checksum_sha256,
        "encrypted": artifact.encrypted,
        "created_at": artifact.created_at.isoformat(),
        "note": artifact.note,
        **details,
    }


@router.post("/restore")
def restore_backup(payload: BackupRestoreRequest, db: Session = Depends(get_db)) -> dict:
    artifact = db.get(BackupArtifact, payload.backup_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Backup not found")

    restored = restore_from_backup_artifact(db, artifact)
    return {
        "backup_id": artifact.id,
        "backup_path": artifact.backup_path,
        **restored,
    }
