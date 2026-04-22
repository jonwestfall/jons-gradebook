from __future__ import annotations

import base64
import hashlib
import json
import shutil
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.db.models import BackupArtifact
from app.db.models.common import Base


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _collect_storage_files(storage_root: Path) -> list[dict[str, Any]]:
    if not storage_root.exists():
        return []

    files: list[dict[str, Any]] = []
    for file_path in sorted(storage_root.rglob("*")):
        if not file_path.is_file():
            continue
        raw = file_path.read_bytes()
        files.append(
            {
                "path": str(file_path.relative_to(storage_root)),
                "size": len(raw),
                "content_b64": base64.b64encode(raw).decode("ascii"),
            }
        )
    return files


def _backup_payload(db: Session) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "default_timezone": settings.default_timezone,
            "app_name": settings.app_name,
        },
        "tables": {},
        "files": _collect_storage_files(storage_root),
    }

    for table in Base.metadata.sorted_tables:
        rows = db.execute(select(table)).mappings().all()
        payload["tables"][table.name] = [
            {column: _normalize_value(value) for column, value in row.items()} for row in rows
        ]

    return payload


def create_encrypted_backup(db: Session, note: str | None = None) -> BackupArtifact:
    settings = get_settings()
    backup_root = Path(settings.backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    payload = _backup_payload(db)

    json_blob = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    encrypted_blob = encrypt_bytes(json_blob)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_root / f"gradebook-backup-{timestamp}.json.enc"
    backup_path.write_bytes(encrypted_blob)

    artifact = BackupArtifact(
        backup_path=str(backup_path),
        checksum_sha256=hashlib.sha256(encrypted_blob).hexdigest(),
        encrypted=True,
        note=note,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def load_backup_payload(artifact: BackupArtifact) -> dict[str, Any]:
    encrypted_blob = Path(artifact.backup_path).read_bytes()
    raw_blob = decrypt_bytes(encrypted_blob)
    payload = json.loads(raw_blob.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Backup payload is invalid")
    return payload


def inspect_backup(artifact: BackupArtifact) -> dict[str, Any]:
    payload = load_backup_payload(artifact)
    table_counts = {
        table_name: len(rows) if isinstance(rows, list) else 0
        for table_name, rows in (payload.get("tables") or {}).items()
    }
    return {
        "generated_at": payload.get("generated_at"),
        "settings": payload.get("settings") or {},
        "table_counts": table_counts,
        "file_count": len(payload.get("files") or []),
    }


def inspect_current_state(db: Session) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)

    table_counts: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        table_counts[table.name] = int(db.execute(select(func.count()).select_from(table)).scalar_one())

    file_count = 0
    if storage_root.exists():
        file_count = sum(1 for path in storage_root.rglob("*") if path.is_file())

    return {
        "table_counts": table_counts,
        "file_count": file_count,
    }


def restore_from_backup_artifact(db: Session, artifact: BackupArtifact) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)

    payload = load_backup_payload(artifact)
    backup_tables = payload.get("tables") or {}
    backup_files = payload.get("files") or []

    # Keep the backup artifact table intact so restore does not erase available restore points.
    restorable_tables = [table for table in Base.metadata.sorted_tables if table.name != "backup_artifacts"]

    with db.begin():
        for table in restorable_tables:
            db.execute(delete(table))

        for table in restorable_tables:
            rows = backup_tables.get(table.name) or []
            if rows:
                db.execute(table.insert(), rows)

    if storage_root.exists():
        for child in storage_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    restored_files = 0
    for file_entry in backup_files:
        rel_path = str(file_entry.get("path") or "").strip()
        content_b64 = file_entry.get("content_b64")
        if not rel_path or not isinstance(content_b64, str):
            continue
        target_path = storage_root / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(base64.b64decode(content_b64.encode("ascii")))
        restored_files += 1

    return {
        "restored_tables": len(restorable_tables),
        "restored_files": restored_files,
        "generated_at": payload.get("generated_at"),
    }
