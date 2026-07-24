from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import shutil
import tempfile
from datetime import date, datetime, time, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from uuid import uuid4

from cryptography.fernet import InvalidToken
from sqlalchemy import Date, DateTime, Time, delete, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.schema import Table

from app.core.config import get_settings
from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.db.models import BackupArtifact
from app.db.models.common import Base


BACKUP_FORMAT_VERSION = 1


class BackupValidationError(ValueError):
    """Raised when an artifact cannot be safely inspected or restored."""


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat()
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
        if file_path.is_symlink():
            raise BackupValidationError(f"Storage contains an unsupported symbolic link: {file_path}")
        if not file_path.is_file():
            continue
        raw = file_path.read_bytes()
        files.append(
            {
                "path": file_path.relative_to(storage_root).as_posix(),
                "size": len(raw),
                "checksum_sha256": hashlib.sha256(raw).hexdigest(),
                "content_b64": base64.b64encode(raw).decode("ascii"),
            }
        )
    return files


def _backup_payload(db: Session) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)

    payload: dict[str, Any] = {
        "format_version": BACKUP_FORMAT_VERSION,
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

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_root / f"gradebook-backup-{timestamp}.json.enc"
    backup_path.write_bytes(encrypted_blob)

    artifact = BackupArtifact(
        backup_path=str(backup_path),
        checksum_sha256=hashlib.sha256(encrypted_blob).hexdigest(),
        encrypted=True,
        note=note,
    )
    try:
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except Exception:
        db.rollback()
        backup_path.unlink(missing_ok=True)
        raise
    return artifact


def _validated_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BackupValidationError("Backup payload is not an object")

    format_version = payload.get("format_version", 1)
    if type(format_version) is not int or format_version != BACKUP_FORMAT_VERSION:
        raise BackupValidationError(
            f"Unsupported backup format version {format_version!r}; expected {BACKUP_FORMAT_VERSION}"
        )

    tables = payload.get("tables")
    files = payload.get("files")
    if not isinstance(tables, dict):
        raise BackupValidationError("Backup payload has an invalid tables section")
    if not isinstance(files, list):
        raise BackupValidationError("Backup payload has an invalid files section")

    known_tables = set(Base.metadata.tables)
    unknown_tables = set(tables) - known_tables
    if unknown_tables:
        names = ", ".join(sorted(unknown_tables))
        raise BackupValidationError(f"Backup contains tables unknown to this application version: {names}")

    for table_name, rows in tables.items():
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise BackupValidationError(f"Backup table {table_name!r} has invalid row data")

    return payload


def load_backup_payload(artifact: BackupArtifact) -> dict[str, Any]:
    if not artifact.encrypted:
        raise BackupValidationError("Backup artifact is not marked as encrypted")

    backup_path = Path(artifact.backup_path)
    try:
        encrypted_blob = backup_path.read_bytes()
    except OSError as exc:
        raise BackupValidationError("Backup artifact cannot be read") from exc

    actual_checksum = hashlib.sha256(encrypted_blob).hexdigest()
    if not hmac.compare_digest(actual_checksum, artifact.checksum_sha256):
        raise BackupValidationError("Backup artifact checksum does not match its recorded checksum")

    try:
        raw_blob = decrypt_bytes(encrypted_blob)
    except (InvalidToken, ValueError) as exc:
        raise BackupValidationError("Backup artifact could not be decrypted with the configured key") from exc

    try:
        payload = json.loads(raw_blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupValidationError("Backup artifact does not contain valid JSON") from exc
    return _validated_payload(payload)


def inspect_backup(artifact: BackupArtifact) -> dict[str, Any]:
    payload = load_backup_payload(artifact)
    table_counts = {table_name: len(rows) for table_name, rows in payload["tables"].items()}
    return {
        "format_version": payload.get("format_version", 1),
        "generated_at": payload.get("generated_at"),
        "settings": payload.get("settings") or {},
        "table_counts": table_counts,
        "file_count": len(payload["files"]),
    }


def inspect_current_state(db: Session) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)

    table_counts: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        table_counts[table.name] = int(db.execute(select(func.count()).select_from(table)).scalar_one())

    file_count = 0
    if storage_root.exists():
        file_count = sum(1 for path in storage_root.rglob("*") if path.is_file() and not path.is_symlink())

    return {
        "table_counts": table_counts,
        "file_count": file_count,
    }


def _safe_relative_path(raw_path: Any) -> PurePosixPath:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise BackupValidationError("Backup contains a file with an empty path")

    windows_path = PureWindowsPath(raw_path)
    normalized = PurePosixPath(raw_path.replace("\\", "/"))
    if windows_path.is_absolute() or windows_path.drive or normalized.is_absolute():
        raise BackupValidationError(f"Backup contains an absolute file path: {raw_path!r}")
    if any(part in {"", ".", ".."} for part in normalized.parts):
        raise BackupValidationError(f"Backup contains an unsafe file path: {raw_path!r}")
    return normalized


def _decode_file_entry(file_entry: Any) -> tuple[PurePosixPath, bytes]:
    if not isinstance(file_entry, dict):
        raise BackupValidationError("Backup contains an invalid file entry")

    relative_path = _safe_relative_path(file_entry.get("path"))
    content_b64 = file_entry.get("content_b64")
    if not isinstance(content_b64, str):
        raise BackupValidationError(f"Backup file {relative_path} has no encoded content")

    try:
        content = base64.b64decode(content_b64.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise BackupValidationError(f"Backup file {relative_path} has invalid encoded content") from exc

    recorded_size = file_entry.get("size")
    if recorded_size is not None and (not isinstance(recorded_size, int) or recorded_size != len(content)):
        raise BackupValidationError(f"Backup file {relative_path} does not match its recorded size")

    recorded_checksum = file_entry.get("checksum_sha256")
    if recorded_checksum is not None:
        actual_checksum = hashlib.sha256(content).hexdigest()
        if not isinstance(recorded_checksum, str) or not hmac.compare_digest(actual_checksum, recorded_checksum):
            raise BackupValidationError(f"Backup file {relative_path} does not match its recorded checksum")

    return relative_path, content


def _stage_backup_files(storage_root: Path, file_entries: list[Any]) -> Path:
    resolved_root = storage_root.resolve()
    if resolved_root == Path(resolved_root.anchor):
        raise BackupValidationError("Refusing to restore into a filesystem root")

    storage_root.parent.mkdir(parents=True, exist_ok=True)
    staged_root = Path(tempfile.mkdtemp(prefix=f".{storage_root.name}-restore-", dir=storage_root.parent))
    seen_paths: set[PurePosixPath] = set()
    try:
        for file_entry in file_entries:
            relative_path, content = _decode_file_entry(file_entry)
            if relative_path in seen_paths:
                raise BackupValidationError(f"Backup contains a duplicate file path: {relative_path}")
            seen_paths.add(relative_path)

            target_path = staged_root.joinpath(*relative_path.parts)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(content)
        return staged_root
    except Exception:
        shutil.rmtree(staged_root, ignore_errors=True)
        raise


def _coerce_row_for_table(table: Table, row: dict[str, Any]) -> dict[str, Any]:
    unknown_columns = set(row) - set(table.columns.keys())
    if unknown_columns:
        names = ", ".join(sorted(unknown_columns))
        raise BackupValidationError(f"Backup table {table.name!r} contains unknown columns: {names}")

    coerced = dict(row)
    for column in table.columns:
        value = coerced.get(column.name)
        if value is None or not isinstance(value, str):
            continue
        try:
            if isinstance(column.type, DateTime):
                coerced[column.name] = datetime.fromisoformat(value)
            elif isinstance(column.type, Date):
                coerced[column.name] = date.fromisoformat(value)
            elif isinstance(column.type, Time):
                coerced[column.name] = time.fromisoformat(value)
        except ValueError as exc:
            raise BackupValidationError(
                f"Backup table {table.name!r} has an invalid value for {column.name!r}"
            ) from exc
    return coerced


def _reset_postgres_sequences(db: Session, tables: list[Table]) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return

    preparer = db.get_bind().dialect.identifier_preparer
    for table in tables:
        column = table.autoincrement_column
        if column is None:
            continue

        sequence_name = db.scalar(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {"table_name": table.fullname, "column_name": column.name},
        )
        if not sequence_name:
            continue

        quoted_table = preparer.format_table(table)
        quoted_column = preparer.quote(column.name)
        max_value = db.scalar(text(f"SELECT MAX({quoted_column}) FROM {quoted_table}"))
        db.execute(
            text("SELECT setval(CAST(:sequence_name AS regclass), :value, :is_called)"),
            {
                "sequence_name": sequence_name,
                "value": max(int(max_value or 1), 1),
                "is_called": max_value is not None,
            },
        )


def restore_from_backup_artifact(db: Session, artifact: BackupArtifact) -> dict[str, Any]:
    settings = get_settings()
    storage_root = Path(settings.storage_root)

    # Fully validate and stage every file before changing the database or live storage.
    payload = load_backup_payload(artifact)
    backup_tables = payload["tables"]
    staged_root = _stage_backup_files(storage_root, payload["files"])

    # Keep restore points available. Dependency order is parent-to-child for inserts
    # and must be reversed for deletes to satisfy foreign keys.
    restorable_tables = [table for table in Base.metadata.sorted_tables if table.name != "backup_artifacts"]
    previous_root = storage_root.parent / f".{storage_root.name}-pre-restore-{uuid4().hex}"
    previous_storage_moved = False
    storage_swapped = False
    cleanup_warning: str | None = None

    try:
        for table in reversed(restorable_tables):
            db.execute(delete(table))

        for table in restorable_tables:
            rows = [_coerce_row_for_table(table, row) for row in (backup_tables.get(table.name) or [])]
            if rows:
                db.execute(table.insert(), rows)

        _reset_postgres_sequences(db, restorable_tables)

        if storage_root.exists() or storage_root.is_symlink():
            storage_root.replace(previous_root)
            previous_storage_moved = True
        staged_root.replace(storage_root)
        storage_swapped = True

        db.commit()
    except Exception:
        db.rollback()
        if storage_swapped:
            if storage_root.is_dir() and not storage_root.is_symlink():
                shutil.rmtree(storage_root)
            elif storage_root.exists() or storage_root.is_symlink():
                storage_root.unlink()
        if previous_storage_moved and (previous_root.exists() or previous_root.is_symlink()):
            previous_root.replace(storage_root)
        shutil.rmtree(staged_root, ignore_errors=True)
        raise

    if previous_storage_moved and (previous_root.exists() or previous_root.is_symlink()):
        try:
            if previous_root.is_dir() and not previous_root.is_symlink():
                shutil.rmtree(previous_root)
            else:
                previous_root.unlink()
        except OSError as exc:
            cleanup_warning = f"Restore succeeded, but previous storage cleanup failed: {exc}"

    result: dict[str, Any] = {
        "restored_tables": len(restorable_tables),
        "restored_files": len(payload["files"]),
        "generated_at": payload.get("generated_at"),
    }
    if cleanup_warning:
        result["warning"] = cleanup_warning
    return result
