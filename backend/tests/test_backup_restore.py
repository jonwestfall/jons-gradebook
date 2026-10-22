"""Backup, import, download, and restore behavior (issue #2)."""

import base64
import json
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.router import api_router
from app.core.encryption import decrypt_bytes, encrypt_bytes
from app.db.models import BackupArtifact, StoredDocument, StudentProfile
from app.db.session import get_db
from tests.pg_support import alembic_config, requires_postgres, throwaway_database


def _seed(client: TestClient, db: Session) -> dict:
    ada = StudentProfile(first_name="Ada", last_name="Lovelace")
    grace = StudentProfile(first_name="Grace", last_name="Hopper")
    db.add_all([ada, grace])
    db.commit()
    response = client.post(
        "/api/v1/documents/upload",
        data={"owner_type": "student", "owner_id": ada.id, "title": "Lab notes"},
        files={"file": ("notes.txt", b"original lab notes", "text/plain")},
    )
    assert response.status_code == 200
    return {"ada_id": ada.id, "grace_id": grace.id, "document_id": response.json()["id"]}


def _create_backup(client: TestClient, note: str = "test") -> int:
    response = client.post("/api/v1/backup/", json={"note": note})
    assert response.status_code == 200
    return response.json()["id"]


def _student_names(db: Session) -> list[str]:
    db.expire_all()
    return sorted(student.first_name for student in db.scalars(select(StudentProfile)).all())


def _import_payload(client: TestClient, payload: dict) -> int:
    blob = encrypt_bytes(json.dumps(payload).encode("utf-8"))
    response = client.post("/api/v1/backup/import", files={"file": ("crafted.json.enc", blob, "application/octet-stream")})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _payload_of(db: Session, backup_id: int) -> dict:
    artifact = db.get(BackupArtifact, backup_id)
    return json.loads(decrypt_bytes(Path(artifact.backup_path).read_bytes()))


def test_restore_round_trip_restores_rows_and_files(client, db_session: Session, isolated_storage):
    seeded = _seed(client, db_session)
    backup_id = _create_backup(client, "before changes")

    # Diverge from the backup: rename, add a student, overwrite the stored file, add a stray file.
    db_session.get(StudentProfile, seeded["ada_id"]).first_name = "Changed"
    db_session.add(StudentProfile(first_name="Extra", last_name="Student"))
    db_session.commit()
    stored_files = [path for path in isolated_storage["storage"].rglob("*") if path.is_file()]
    stored_files[0].write_bytes(b"tampered")
    (isolated_storage["storage"] / "stray.txt").write_text("not in backup")

    response = client.post("/api/v1/backup/restore", json={"backup_id": backup_id})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["restored_files"] == 1
    assert result["safety_backup_id"] is not None

    assert _student_names(db_session) == ["Ada", "Grace"]
    assert not (isolated_storage["storage"] / "stray.txt").exists()
    assert not [path for path in isolated_storage["storage"].iterdir() if path.name.startswith(".restore-")]
    download = client.get(f"/api/v1/documents/{seeded['document_id']}/download")
    assert download.status_code == 200
    assert download.content == b"original lab notes"

    # Backup artifacts are never wiped by a restore, and the safety backup holds the pre-restore state.
    ids = {row["id"] for row in client.get("/api/v1/backup/").json()}
    assert {backup_id, result["safety_backup_id"]} <= ids
    safety_names = sorted(row["first_name"] for row in _payload_of(db_session, result["safety_backup_id"])["tables"]["student_profiles"])
    assert safety_names == ["Changed", "Extra", "Grace"]


def test_failed_restore_leaves_database_and_files_untouched(client, db_session: Session, isolated_storage):
    seeded = _seed(client, db_session)
    payload = _payload_of(db_session, _create_backup(client))
    # A row that violates NOT NULL makes the insert fail after the existing rows were deleted.
    payload["tables"]["student_profiles"].append({"id": 999, "first_name": None, "last_name": "Broken"})
    payload["files"].append({"path": "documents/new-file.bin", "size": 3, "content_b64": base64.b64encode(b"new").decode()})
    broken_id = _import_payload(client, payload)

    files_before = sorted(str(path) for path in isolated_storage["storage"].rglob("*"))
    response = client.post("/api/v1/backup/restore", json={"backup_id": broken_id, "create_safety_backup": False})
    assert response.status_code == 422
    assert "rolled back" in response.json()["detail"]

    assert _student_names(db_session) == ["Ada", "Grace"]
    assert sorted(str(path) for path in isolated_storage["storage"].rglob("*")) == files_before
    assert client.get(f"/api/v1/documents/{seeded['document_id']}/download").content == b"original lab notes"


def test_unsafe_file_paths_are_rejected_before_any_change(client, db_session: Session, isolated_storage, tmp_path):
    _seed(client, db_session)
    payload = _payload_of(db_session, _create_backup(client))
    payload["tables"]["student_profiles"] = []
    payload["files"] = [{"path": "../escaped.txt", "size": 1, "content_b64": base64.b64encode(b"x").decode()}]
    unsafe_id = _import_payload(client, payload)

    preflight = client.get(f"/api/v1/backup/{unsafe_id}/preflight").json()
    assert preflight["can_restore"] is False
    assert any("unsafe file path" in warning for warning in preflight["warnings"])

    response = client.post("/api/v1/backup/restore", json={"backup_id": unsafe_id})
    assert response.status_code == 422
    assert not (tmp_path / "escaped.txt").exists()
    assert _student_names(db_session) == ["Ada", "Grace"]


def test_modified_backup_file_fails_checksum(client, db_session: Session):
    _seed(client, db_session)
    backup_id = _create_backup(client)
    artifact = db_session.get(BackupArtifact, backup_id)
    path = Path(artifact.backup_path)
    path.write_bytes(path.read_bytes() + b"corruption")

    assert client.get(f"/api/v1/backup/{backup_id}/preflight").status_code == 422
    response = client.post("/api/v1/backup/restore", json={"backup_id": backup_id})
    assert response.status_code == 422
    assert "checksum" in response.json()["detail"]


def test_schema_revision_mismatch_is_refused(client, db_session: Session):
    db_session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
    db_session.execute(text("INSERT INTO alembic_version (version_num) VALUES ('rev_current')"))
    db_session.commit()
    _seed(client, db_session)
    payload = _payload_of(db_session, _create_backup(client))
    assert payload["alembic_revision"] == "rev_current"
    assert payload["format_version"] == 2

    payload["alembic_revision"] = "rev_older"
    older_id = _import_payload(client, payload)
    preflight = client.get(f"/api/v1/backup/{older_id}/preflight").json()
    assert preflight["can_restore"] is False
    assert preflight["backup_alembic_revision"] == "rev_older"
    assert preflight["current_alembic_revision"] == "rev_current"

    response = client.post("/api/v1/backup/restore", json={"backup_id": older_id})
    assert response.status_code == 409
    assert _student_names(db_session) == ["Ada", "Grace"]


def test_legacy_backup_without_revision_restores_with_warning(client, db_session: Session):
    _seed(client, db_session)
    payload = _payload_of(db_session, _create_backup(client))
    del payload["alembic_revision"]
    del payload["format_version"]
    legacy_id = _import_payload(client, payload)
    db_session.add(StudentProfile(first_name="Extra", last_name="Student"))
    db_session.commit()

    response = client.post("/api/v1/backup/restore", json={"backup_id": legacy_id, "create_safety_backup": False})
    assert response.status_code == 200, response.text
    assert response.json()["warnings"]
    assert response.json()["safety_backup_id"] is None
    assert _student_names(db_session) == ["Ada", "Grace"]


def test_import_rejects_files_that_are_not_backups(client):
    response = client.post("/api/v1/backup/import", files={"file": ("junk.bin", b"not a backup", "application/octet-stream")})
    assert response.status_code == 422
    assert "decrypted" in response.json()["detail"]

    not_a_payload = encrypt_bytes(json.dumps(["wrong", "shape"]).encode("utf-8"))
    response = client.post("/api/v1/backup/import", files={"file": ("list.enc", not_a_payload, "application/octet-stream")})
    assert response.status_code == 422


def test_download_returns_exact_artifact_bytes(client, db_session: Session):
    _seed(client, db_session)
    backup_id = _create_backup(client)
    artifact = db_session.get(BackupArtifact, backup_id)

    response = client.get(f"/api/v1/backup/{backup_id}/download")
    assert response.status_code == 200
    assert response.content == Path(artifact.backup_path).read_bytes()
    assert "attachment" in response.headers["content-disposition"]


@pytest.fixture()
def postgres_session_factory() -> Generator[callable, None, None]:
    """Create migrated PostgreSQL databases on demand; each one is a separate 'machine'."""
    engines = []
    contexts = []

    def make() -> sessionmaker:
        context = throwaway_database("gradebook_restore")
        database_url = context.__enter__()
        contexts.append(context)
        command.upgrade(alembic_config(database_url), "head")
        engine = create_engine(database_url)
        engines.append(engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    yield make
    for engine in engines:
        engine.dispose()
    for context in reversed(contexts):
        context.__exit__(None, None, None)


def _client_for(session_factory: sessionmaker) -> TestClient:
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@requires_postgres
def test_disaster_recovery_restore_onto_a_new_postgres_database(postgres_session_factory, isolated_storage, monkeypatch):
    from app.core.config import get_settings

    # Machine A: real data, then download its backup file.
    machine_a = postgres_session_factory()
    client_a = _client_for(machine_a)
    with machine_a() as db:
        seeded = _seed(client_a, db)
    backup_id = _create_backup(client_a)
    backup_file = client_a.get(f"/api/v1/backup/{backup_id}/download").content

    # Machine B: brand-new database and empty storage volume.
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_root", str(isolated_storage["storage"].parent / "machine-b-storage"))
    monkeypatch.setattr(settings, "backup_root", str(isolated_storage["backups"].parent / "machine-b-backups"))
    machine_b = postgres_session_factory()
    client_b = _client_for(machine_b)

    imported = client_b.post("/api/v1/backup/import", files={"file": ("from-machine-a.json.enc", backup_file, "application/octet-stream")})
    assert imported.status_code == 200, imported.text
    preflight = client_b.get(f"/api/v1/backup/{imported.json()['id']}/preflight").json()
    assert preflight["can_restore"] is True
    assert preflight["backup_alembic_revision"] == preflight["current_alembic_revision"]

    restored = client_b.post("/api/v1/backup/restore", json={"backup_id": imported.json()["id"]})
    assert restored.status_code == 200, restored.text
    assert restored.json()["restored_files"] == 1

    with machine_b() as db:
        assert sorted(s.first_name for s in db.scalars(select(StudentProfile)).all()) == ["Ada", "Grace"]
        # Sequences must be past the restored ids, or the next insert hits a duplicate key.
        db.add(StudentProfile(first_name="New", last_name="Student"))
        db.add(StoredDocument(owner_type="student", owner_id=seeded["ada_id"], title="t", document_type="txt", current_version=1))
        db.commit()
        assert db.scalar(select(func.count()).select_from(StudentProfile)) == 3
    assert client_b.get(f"/api/v1/documents/{seeded['document_id']}/download").content == b"original lab notes"
    # A new upload also gets a fresh id and works end to end.
    upload = client_b.post(
        "/api/v1/documents/upload",
        data={"owner_type": "student", "owner_id": seeded["grace_id"], "title": "After restore"},
        files={"file": ("after.txt", b"post-restore upload", "text/plain")},
    )
    assert upload.status_code == 200, upload.text


@requires_postgres
def test_restore_over_existing_postgres_data_respects_foreign_keys(postgres_session_factory):
    machine = postgres_session_factory()
    client = _client_for(machine)
    with machine() as db:
        seeded = _seed(client, db)
    template_id = client.get("/api/v1/llm/instructions").json()[0]["id"]
    # llm_workbench_jobs -> llm_instruction_templates is ON DELETE RESTRICT, so the wipe must go children-first.
    job = client.post(
        "/api/v1/llm/workbench/jobs",
        data={"student_id": seeded["ada_id"], "instruction_template_id": template_id, "source_document_id": seeded["document_id"]},
    )
    assert job.status_code == 200, job.text
    backup_id = _create_backup(client)

    with machine() as db:
        db.add(StudentProfile(first_name="Extra", last_name="Student"))
        db.commit()

    restored = client.post("/api/v1/backup/restore", json={"backup_id": backup_id})
    assert restored.status_code == 200, restored.text
    with machine() as db:
        assert sorted(s.first_name for s in db.scalars(select(StudentProfile)).all()) == ["Ada", "Grace"]
        assert db.scalar(text("SELECT count(*) FROM llm_workbench_jobs")) == 1
