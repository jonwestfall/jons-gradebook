import hashlib
import json
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_bytes, encrypt_bytes, get_fernet
from app.db.models import BackupArtifact, Task, TaskPriority, TaskStatus
from app.services.backup import create_encrypted_backup


@pytest.fixture()
def backup_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Path, Path], None, None]:
    storage_root = tmp_path / "storage"
    backup_root = tmp_path / "backups"
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_root", str(storage_root))
    monkeypatch.setattr(settings, "backup_root", str(backup_root))
    get_fernet.cache_clear()
    yield storage_root, backup_root
    get_fernet.cache_clear()


def _rewrite_artifact(artifact: BackupArtifact, db: Session, mutate) -> None:
    artifact_path = Path(artifact.backup_path)
    payload = json.loads(decrypt_bytes(artifact_path.read_bytes()).decode("utf-8"))
    mutate(payload)
    encrypted_blob = encrypt_bytes(json.dumps(payload).encode("utf-8"))
    artifact_path.write_bytes(encrypted_blob)
    artifact.checksum_sha256 = hashlib.sha256(encrypted_blob).hexdigest()
    db.commit()


def test_restore_requires_server_side_confirmation(client) -> None:
    response = client.post("/api/v1/backup/restore", json={"backup_id": 1})
    assert response.status_code == 422

    response = client.post(
        "/api/v1/backup/restore",
        json={"backup_id": 1, "confirmation": "restore"},
    )
    assert response.status_code == 422


def test_restore_replaces_database_and_storage_from_validated_artifact(
    client,
    db_session: Session,
    backup_paths: tuple[Path, Path],
) -> None:
    storage_root, _backup_root = backup_paths
    stored_file = storage_root / "documents" / "example.bin"
    stored_file.parent.mkdir(parents=True)
    stored_file.write_bytes(b"original encrypted document")

    task = Task(
        title="Original follow-up",
        status=TaskStatus.open,
        priority=TaskPriority.high,
        source="manual",
    )
    db_session.add(task)
    db_session.commit()
    task_id = task.id

    artifact = create_encrypted_backup(db_session, note="restore regression")
    artifact_id = artifact.id

    task.title = "Changed after backup"
    stored_file.write_bytes(b"changed content")
    extra_file = storage_root / "documents" / "not-in-backup.bin"
    extra_file.write_bytes(b"remove me")
    db_session.commit()

    response = client.post(
        "/api/v1/backup/restore",
        json={"backup_id": artifact_id, "confirmation": "RESTORE"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["restored_files"] == 1

    db_session.expire_all()
    restored_task = db_session.scalar(select(Task).where(Task.id == task_id))
    assert restored_task is not None
    assert restored_task.title == "Original follow-up"
    assert db_session.get(BackupArtifact, artifact_id) is not None
    assert stored_file.read_bytes() == b"original encrypted document"
    assert not extra_file.exists()
    assert not list(storage_root.parent.glob(f".{storage_root.name}-pre-restore-*"))


def test_tampered_artifact_is_rejected_before_restore(
    client,
    db_session: Session,
    backup_paths: tuple[Path, Path],
) -> None:
    storage_root, _backup_root = backup_paths
    marker = storage_root / "marker.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("before", encoding="utf-8")
    artifact = create_encrypted_backup(db_session)
    artifact_id = artifact.id

    artifact_path = Path(artifact.backup_path)
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tampered")

    response = client.post(
        "/api/v1/backup/restore",
        json={"backup_id": artifact_id, "confirmation": "RESTORE"},
    )
    assert response.status_code == 400
    assert "checksum" in response.json()["detail"].lower()
    assert marker.read_text(encoding="utf-8") == "before"


def test_unsafe_backup_file_path_is_rejected_before_restore(
    client,
    db_session: Session,
    backup_paths: tuple[Path, Path],
) -> None:
    storage_root, _backup_root = backup_paths
    marker = storage_root / "marker.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("live data", encoding="utf-8")
    artifact = create_encrypted_backup(db_session)
    artifact_id = artifact.id

    def add_unsafe_file(payload: dict) -> None:
        payload["files"] = [
            {
                "path": "../escaped.txt",
                "size": 4,
                "checksum_sha256": hashlib.sha256(b"oops").hexdigest(),
                "content_b64": "b29wcw==",
            }
        ]

    _rewrite_artifact(artifact, db_session, add_unsafe_file)

    response = client.post(
        "/api/v1/backup/restore",
        json={"backup_id": artifact_id, "confirmation": "RESTORE"},
    )
    assert response.status_code == 400
    assert "unsafe file path" in response.json()["detail"].lower()
    assert marker.read_text(encoding="utf-8") == "live data"
    assert not (storage_root.parent / "escaped.txt").exists()
