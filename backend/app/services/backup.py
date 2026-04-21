from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import encrypt_bytes
from app.db.models import BackupArtifact
from app.db.models.common import Base


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def create_encrypted_backup(db: Session, note: str | None = None) -> BackupArtifact:
    settings = get_settings()
    backup_root = Path(settings.backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }

    for table in Base.metadata.sorted_tables:
        rows = db.execute(select(table)).mappings().all()
        payload["tables"][table.name] = [
            {column: _normalize_value(value) for column, value in row.items()} for row in rows
        ]

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
