from __future__ import annotations

import base64
import hashlib
import json
import shutil
import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Date, DateTime, Time, delete, func, inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.db.models import BackupArtifact
from app.db.models.common import Base

BACKUP_FORMAT_VERSION = 2
# The artifact table is never restored, so restoring cannot erase available restore points.
EXCLUDED_TABLES = {"backup_artifacts"}
# Scratch directories created inside STORAGE_ROOT while a restore swaps files.
RESTORE_SCRATCH_PREFIX = ".restore-"


class BackupError(ValueError):
    """A backup artifact cannot be read, verified, or applied."""


class BackupIntegrityError(BackupError):
    """The artifact is unreadable, corrupted, or was encrypted with a different key."""


class BackupCompatibilityError(BackupError):
    """The artifact was created for a different database schema revision."""


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _restore_value(column: Any, value: Any) -> Any:
    """Turn a JSON-normalized backup value back into what the column type expects."""
    if value is None or not isinstance(value, str):
        return value
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value)
    if isinstance(column.type, Date):
        return date.fromisoformat(value)
    if isinstance(column.type, Time):
        return time.fromisoformat(value)
    return value


def _is_restore_scratch(path: Path, storage_root: Path) -> bool:
    relative = path.relative_to(storage_root)
    return bool(relative.parts) and relative.parts[0].startswith(RESTORE_SCRATCH_PREFIX)


def _collect_storage_files(storage_root: Path) -> list[dict[str, Any]]:
    if not storage_root.exists():
        return []

    files: list[dict[str, Any]] = []
    for file_path in sorted(storage_root.rglob("*")):
        if not file_path.is_file() or _is_restore_scratch(file_path, storage_root):
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


def current_schema_revision(db: Session) -> str | None:
    """Return the Alembic revision of the connected database, or None when unmanaged."""
    if not inspect(db.connection()).has_table("alembic_version"):
        return None
    return db.execute(text("SELECT version_num FROM alembic_version")).scalar()


def _backup_payload(db: Session) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)

    payload: dict[str, Any] = {
        "format_version": BACKUP_FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alembic_revision": current_schema_revision(db),
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


def _write_artifact(db: Session, encrypted_blob: bytes, label: str, note: str | None) -> BackupArtifact:
    backup_root = Path(get_settings().backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_root / f"gradebook-{label}-{timestamp}.json.enc"
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


def create_encrypted_backup(db: Session, note: str | None = None) -> BackupArtifact:
    payload = _backup_payload(db)
    json_blob = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    return _write_artifact(db, encrypt_bytes(json_blob), "backup", note)


def _decode_payload(encrypted_blob: bytes) -> dict[str, Any]:
    try:
        raw_blob = decrypt_bytes(encrypted_blob)
    except Exception as exc:
        raise BackupIntegrityError(
            "Backup could not be decrypted. It may be corrupted or encrypted with a different ENCRYPTION_KEY."
        ) from exc
    try:
        payload = json.loads(raw_blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupIntegrityError("Backup decrypted but does not contain valid backup data.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), dict):
        raise BackupIntegrityError("Backup payload is invalid.")
    return payload


def load_backup_payload(artifact: BackupArtifact) -> dict[str, Any]:
    path = Path(artifact.backup_path)
    if not path.is_file():
        raise BackupIntegrityError(f"Backup file is missing: {path}")
    encrypted_blob = path.read_bytes()
    if hashlib.sha256(encrypted_blob).hexdigest() != artifact.checksum_sha256:
        raise BackupIntegrityError("Backup file checksum does not match the recorded checksum; the file has changed.")
    return _decode_payload(encrypted_blob)


def import_backup_file(db: Session, content: bytes, original_filename: str | None = None) -> BackupArtifact:
    """Register an uploaded backup file (for example one copied from another machine)."""
    if not content:
        raise BackupIntegrityError("Uploaded backup file is empty.")
    _decode_payload(content)
    note = f"Imported from {Path(original_filename).name}" if original_filename else "Imported backup"
    return _write_artifact(db, content, "imported", note)


def inspect_backup(artifact: BackupArtifact) -> dict[str, Any]:
    payload = load_backup_payload(artifact)
    table_counts = {
        table_name: len(rows) if isinstance(rows, list) else 0
        for table_name, rows in (payload.get("tables") or {}).items()
    }
    return {
        "generated_at": payload.get("generated_at"),
        "format_version": payload.get("format_version", 1),
        "alembic_revision": payload.get("alembic_revision"),
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
        file_count = sum(
            1 for path in storage_root.rglob("*") if path.is_file() and not _is_restore_scratch(path, storage_root)
        )

    return {
        "table_counts": table_counts,
        "file_count": file_count,
        "alembic_revision": current_schema_revision(db),
    }


def _check_compatibility(payload: dict[str, Any], current_revision: str | None) -> list[str]:
    """Raise when the backup targets another schema; return warnings for legacy backups."""
    backup_revision = payload.get("alembic_revision")
    if backup_revision is None:
        return [
            "This backup predates schema-revision tagging. Restore will fail safely, without changing data, "
            "if its tables do not match the current schema."
        ]
    if current_revision is not None and backup_revision != current_revision:
        raise BackupCompatibilityError(
            f"Backup was created at database revision {backup_revision}, but this database is at "
            f"{current_revision}. Restore it with the matching application version, then upgrade."
        )
    return []


def restore_preflight(db: Session, artifact: BackupArtifact) -> dict[str, Any]:
    payload = load_backup_payload(artifact)
    current_revision = current_schema_revision(db)
    warnings: list[str] = []
    compatible = True
    try:
        warnings.extend(_check_compatibility(payload, current_revision))
    except BackupCompatibilityError as exc:
        compatible = False
        warnings.append(str(exc))
    try:
        _validated_file_entries(payload, Path(get_settings().storage_root))
    except BackupError as exc:
        compatible = False
        warnings.append(str(exc))
    return {
        "payload": payload,
        "backup_alembic_revision": payload.get("alembic_revision"),
        "current_alembic_revision": current_revision,
        "can_restore": compatible,
        "warnings": warnings,
    }


def _validated_file_entries(payload: dict[str, Any], storage_root: Path) -> list[tuple[Path, bytes]]:
    root = storage_root.resolve()
    entries: list[tuple[Path, bytes]] = []
    for file_entry in payload.get("files") or []:
        rel_path = str(file_entry.get("path") or "").strip()
        content_b64 = file_entry.get("content_b64")
        if not rel_path or not isinstance(content_b64, str):
            raise BackupIntegrityError("Backup contains a malformed file entry.")
        target = (root / rel_path).resolve()
        if target == root or root not in target.parents or Path(rel_path).parts[0].startswith(RESTORE_SCRATCH_PREFIX):
            raise BackupIntegrityError(f"Backup contains an unsafe file path: {rel_path}")
        entries.append((target.relative_to(root), base64.b64decode(content_b64.encode("ascii"))))
    return entries


def _prepare_rows(table: Any, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unknown = sorted({key for row in rows for key in row} - set(table.columns.keys()))
    if unknown:
        raise BackupCompatibilityError(
            f"Backup table {table.name} has columns that no longer exist: {', '.join(unknown)}."
        )
    prepared = [
        {name: _restore_value(table.columns[name], value) for name, value in row.items()} for row in rows
    ]
    if "id" in table.columns:
        # Insert parents before children for self-referencing tables.
        prepared.sort(key=lambda row: row.get("id") or 0)
    return prepared


def _reset_sequences(db: Session, tables: list[Any]) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return
    for table in tables:
        if "id" not in table.columns:
            continue
        # Rows are inserted with explicit ids, which does not advance SERIAL sequences.
        db.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                f'COALESCE((SELECT MAX(id) FROM "{table.name}"), 0) + 1, false)'
            ),
            {"table_name": table.name},
        )


class _StorageSwap:
    """Swap STORAGE_ROOT's contents for a staged copy, journaling each move so it can be undone.

    Scratch directories live inside STORAGE_ROOT, so every move is a same-filesystem rename,
    even when STORAGE_ROOT itself is a mount point.
    """

    def __init__(self, storage_root: Path) -> None:
        scratch_id = uuid.uuid4().hex[:12]
        self.storage_root = storage_root
        self.staging = storage_root / f"{RESTORE_SCRATCH_PREFIX}staging-{scratch_id}"
        self.retired = storage_root / f"{RESTORE_SCRATCH_PREFIX}retired-{scratch_id}"
        self._moved_out: list[str] = []
        self._moved_in: list[str] = []
        self._originals_safe = True

    def stage(self, file_entries: list[tuple[Path, bytes]]) -> None:
        self.staging.mkdir()
        for relative_path, content in file_entries:
            target = self.staging / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def swap(self) -> None:
        self.retired.mkdir()
        for child in list(self.storage_root.iterdir()):
            if not child.name.startswith(RESTORE_SCRATCH_PREFIX):
                child.rename(self.retired / child.name)
                self._moved_out.append(child.name)
        for child in list(self.staging.iterdir()):
            child.rename(self.storage_root / child.name)
            self._moved_in.append(child.name)

    def undo(self) -> None:
        self._originals_safe = False
        for name in reversed(self._moved_in):
            (self.storage_root / name).rename(self.staging / name)
        for name in reversed(self._moved_out):
            (self.retired / name).rename(self.storage_root / name)
        self._originals_safe = True

    def cleanup(self) -> None:
        shutil.rmtree(self.staging, ignore_errors=True)
        # Never delete retired originals unless they are no longer needed.
        if self._originals_safe or not self._moved_out:
            shutil.rmtree(self.retired, ignore_errors=True)


def restore_from_backup_artifact(
    db: Session, artifact: BackupArtifact, *, create_safety_backup: bool = True
) -> dict[str, Any]:
    """Replace all database rows and stored files with the contents of a backup.

    The database changes and the file swap succeed or fail together: files are staged
    first, the database is rewritten in one transaction, and the staged files are swapped
    in just before commit. Any failure rolls the database back and restores the old files.
    """
    settings = get_settings()
    storage_root = Path(settings.storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)

    artifact_id = artifact.id
    payload = load_backup_payload(artifact)
    warnings = _check_compatibility(payload, current_schema_revision(db))
    file_entries = _validated_file_entries(payload, storage_root)
    backup_tables = payload.get("tables") or {}

    restorable_tables = [table for table in Base.metadata.sorted_tables if table.name not in EXCLUDED_TABLES]
    prepared_rows = {
        table.name: _prepare_rows(table, backup_tables.get(table.name) or []) for table in restorable_tables
    }
    skipped_tables = sorted(set(backup_tables) - {table.name for table in Base.metadata.sorted_tables})
    if skipped_tables:
        warnings.append(f"Ignored tables that no longer exist: {', '.join(skipped_tables)}.")

    safety_backup_id = None
    if create_safety_backup:
        # Commits its own transaction, so it exists even if the restore below fails.
        safety_backup_id = create_encrypted_backup(db, note=f"Automatic safety backup before restoring #{artifact_id}").id

    storage_swap = _StorageSwap(storage_root)
    try:
        storage_swap.stage(file_entries)

        # Children first so foreign keys (including ON DELETE RESTRICT) never block the wipe.
        for table in reversed(restorable_tables):
            db.execute(delete(table))
        for table in restorable_tables:
            rows = prepared_rows[table.name]
            if rows:
                db.execute(table.insert(), rows)
        _reset_sequences(db, restorable_tables)

        storage_swap.swap()
        db.commit()
    except Exception:
        db.rollback()
        storage_swap.undo()
        raise
    finally:
        storage_swap.cleanup()

    return {
        "backup_id": artifact_id,
        "restored_tables": len(restorable_tables),
        "restored_files": len(file_entries),
        "generated_at": payload.get("generated_at"),
        "alembic_revision": payload.get("alembic_revision"),
        "safety_backup_id": safety_backup_id,
        "warnings": warnings,
    }
