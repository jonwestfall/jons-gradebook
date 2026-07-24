from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.router import api_router
from app.core.config import get_settings
from app.core.encryption import get_fernet
from app.db.models import (
    BackupArtifact,
    Course,
    Enrollment,
    StoredDocumentVersion,
    StudentProfile,
    Task,
    TaskPriority,
    TaskStatus,
)
from app.db.models.common import Base
from app.db.session import get_db


POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")


@pytest.mark.postgres
@pytest.mark.skipif(not POSTGRES_TEST_DATABASE_URL, reason="POSTGRES_TEST_DATABASE_URL is not configured")
def test_postgres_restore_drill_resets_relations_files_and_sequences(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(POSTGRES_TEST_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(delete(table))

    storage_root = tmp_path / "storage"
    backup_root = tmp_path / "backups"
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_root", str(storage_root))
    monkeypatch.setattr(settings, "backup_root", str(backup_root))
    monkeypatch.setattr(settings, "encryption_key", "postgres-restore-drill-key")
    get_fernet.cache_clear()

    session: Session = SessionLocal()
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        student = StudentProfile(first_name="Ada", last_name="Lovelace", email="ada@example.edu")
        course = Course(name="Restore Drill 101")
        session.add_all([student, course])
        session.flush()
        enrollment = Enrollment(course_id=course.id, student_id=student.id)
        original_task = Task(
            title="Original follow-up",
            status=TaskStatus.open,
            priority=TaskPriority.high,
            source="restore_drill",
            linked_student_id=student.id,
            linked_course_id=course.id,
        )
        session.add_all([enrollment, original_task])
        session.commit()
        original_task_id = original_task.id

        with TestClient(app) as client:
            upload_response = client.post(
                "/api/v1/documents/upload",
                data={
                    "owner_type": "student",
                    "owner_id": str(student.id),
                    "title": "Restore drill document",
                    "category": "Student Work",
                },
                files={"file": ("drill.txt", b"original drill document", "text/plain")},
            )
            assert upload_response.status_code == 200, upload_response.text
            document_id = upload_response.json()["id"]
            document_version = session.scalar(
                select(StoredDocumentVersion).where(StoredDocumentVersion.document_id == document_id)
            )
            assert document_version is not None
            stored_file = Path(document_version.encrypted_file_path)

            backup_response = client.post("/api/v1/backup/", json={"note": "PostgreSQL restore drill"})
            assert backup_response.status_code == 200, backup_response.text
            artifact_id = backup_response.json()["id"]

            original_task.title = "Changed after backup"
            later_task = Task(
                title="Should disappear after restore",
                status=TaskStatus.open,
                priority=TaskPriority.low,
                source="restore_drill",
            )
            session.add(later_task)
            session.commit()
            stored_file.write_bytes(b"corrupted after backup")
            extra_file = storage_root / "documents" / "extra.bin"
            extra_file.write_bytes(b"remove during restore")

            preflight_response = client.get(f"/api/v1/backup/{artifact_id}/preflight")
            assert preflight_response.status_code == 200, preflight_response.text
            task_delta = next(
                row for row in preflight_response.json()["table_deltas"] if row["table"] == "tasks"
            )
            assert task_delta == {"table": "tasks", "current_rows": 2, "backup_rows": 1, "delta_rows": -1}

            rejected_response = client.post(
                "/api/v1/backup/restore",
                json={"backup_id": artifact_id, "confirmation": "restore"},
            )
            assert rejected_response.status_code == 422

            restore_response = client.post(
                "/api/v1/backup/restore",
                json={"backup_id": artifact_id, "confirmation": "RESTORE"},
            )
            assert restore_response.status_code == 200, restore_response.text
            assert restore_response.json()["restored_files"] == 1

            download_response = client.get(f"/api/v1/documents/{document_id}/download")
            assert download_response.status_code == 200, download_response.text
            assert download_response.content == b"original drill document"

            for route in [
                "/api/v1/dashboard/summary",
                "/api/v1/students/",
                "/api/v1/courses/",
                "/api/v1/documents/",
                "/api/v1/reports/runs",
                "/api/v1/llm/workbench/jobs",
                "/api/v1/settings/options",
            ]:
                route_response = client.get(route)
                assert route_response.status_code == 200, f"{route}: {route_response.text}"

        # Restore uses bulk table operations, so discard objects that represented
        # the deliberately mutated post-backup state before verifying new rows.
        session.expunge_all()
        restored_task = session.scalar(select(Task).where(Task.id == original_task_id))
        assert restored_task is not None
        assert restored_task.title == "Original follow-up"
        assert restored_task.linked_student_id == student.id
        assert restored_task.linked_course_id == course.id
        assert session.scalar(select(Task).where(Task.title == "Should disappear after restore")) is None
        assert session.get(BackupArtifact, artifact_id) is not None
        assert stored_file.exists()
        assert not extra_file.exists()

        post_restore_task = Task(
            title="Sequence verification",
            status=TaskStatus.open,
            priority=TaskPriority.medium,
            source="restore_drill",
        )
        session.add(post_restore_task)
        session.commit()
        assert post_restore_task.id > original_task_id
    finally:
        session.close()
        app.dependency_overrides.clear()
        get_fernet.cache_clear()
        with engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(delete(table))
        engine.dispose()
