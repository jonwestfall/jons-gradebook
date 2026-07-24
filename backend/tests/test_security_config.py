import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings


def test_development_configuration_keeps_local_defaults_available() -> None:
    settings = Settings(_env_file=None, ENV="development")
    assert settings.env == "development"


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"SECRET_KEY": "replace-me"}, "SECRET_KEY"),
        ({"ENCRYPTION_KEY": ""}, "ENCRYPTION_KEY"),
        (
            {"DATABASE_URL": "postgresql+psycopg://gradebook:gradebook@db:5432/gradebook"},
            "DATABASE_URL",
        ),
    ],
)
def test_production_configuration_rejects_unsafe_defaults(overrides: dict, expected_message: str) -> None:
    values = {
        "ENV": "production",
        "SECRET_KEY": "s" * 32,
        "ENCRYPTION_KEY": "e" * 32,
        "DATABASE_URL": "postgresql+psycopg://gradebook:secure-password@db:5432/gradebook",
        **overrides,
    }
    with pytest.raises(ValidationError, match=expected_message):
        Settings(_env_file=None, **values)


def test_production_configuration_accepts_explicit_secure_values() -> None:
    settings = Settings(
        _env_file=None,
        ENV="production",
        SECRET_KEY="s" * 32,
        ENCRYPTION_KEY="e" * 32,
        DATABASE_URL="postgresql+psycopg://gradebook:secure-password@db:5432/gradebook",
        ALLOWED_HOSTS="localhost,gradebook.example.edu",
    )
    assert settings.allowed_hosts == ["localhost", "gradebook.example.edu"]


def test_application_rejects_untrusted_hosts_and_adds_security_headers(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.main import app, settings

    monkeypatch.setattr(settings, "storage_root", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "backup_root", str(tmp_path / "backups"))

    with TestClient(app) as client:
        rejected = client.get("/api/v1/health/", headers={"host": "untrusted.example"})
        assert rejected.status_code == 400

        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "SAMEORIGIN"
        assert response.headers["referrer-policy"] == "no-referrer"
