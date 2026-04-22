from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanvasStudentFieldMapping
from app.services.canvas.client import CanvasReadClient

ALLOWED_TARGET_FIELDS = [
    "first_name",
    "last_name",
    "email",
    "student_number",
    "institution_name",
]

DEFAULT_MAPPING: dict[str, list[str]] = {
    "first_name": ["user.first_name", "first_name"],
    "last_name": ["user.last_name", "last_name"],
    "email": ["user.email", "user.primary_email", "email", "user.login_id", "login_id"],
    "student_number": ["user.sis_user_id", "sis_user_id", "user.integration_id", "integration_id"],
    "institution_name": ["user.school_name", "school_name", "root_account.name"],
}

COMMON_SOURCE_PATHS = [
    "user.id",
    "user.name",
    "user.first_name",
    "user.last_name",
    "user.sortable_name",
    "user.email",
    "user.primary_email",
    "user.login_id",
    "user.sis_user_id",
    "user.integration_id",
    "sis_user_id",
    "integration_id",
    "email",
    "login_id",
    "sis_import_id",
]


def _deep_get(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def _coerce_clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _compose_source_payload(enrollment_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(enrollment_payload)
    payload.setdefault("user", enrollment_payload.get("user") or {})
    return payload


def get_effective_mapping(db: Session) -> dict[str, list[str]]:
    rows = db.scalars(select(CanvasStudentFieldMapping)).all()
    configured = {row.target_field: [str(path) for path in row.source_paths if str(path).strip()] for row in rows}

    effective: dict[str, list[str]] = {}
    for field in ALLOWED_TARGET_FIELDS:
        effective[field] = configured.get(field) or DEFAULT_MAPPING[field]
    return effective


def list_mapping_config(db: Session) -> list[dict[str, Any]]:
    effective = get_effective_mapping(db)
    return [
        {
            "target_field": field,
            "source_paths": effective[field],
            "default_source_paths": DEFAULT_MAPPING[field],
        }
        for field in ALLOWED_TARGET_FIELDS
    ]


def set_mapping_config(db: Session, target_field: str, source_paths: Iterable[str]) -> dict[str, Any]:
    if target_field not in ALLOWED_TARGET_FIELDS:
        raise ValueError(f"Unsupported target_field: {target_field}")

    cleaned = [str(path).strip() for path in source_paths if str(path).strip()]
    if not cleaned:
        raise ValueError("source_paths cannot be empty")

    row = db.scalar(select(CanvasStudentFieldMapping).where(CanvasStudentFieldMapping.target_field == target_field))
    if not row:
        row = CanvasStudentFieldMapping(target_field=target_field, source_paths=cleaned)
        db.add(row)
    else:
        row.source_paths = cleaned

    db.commit()
    db.refresh(row)
    return {
        "target_field": row.target_field,
        "source_paths": row.source_paths,
    }


def resolve_student_fields(enrollment_payload: dict[str, Any], mapping: dict[str, list[str]]) -> dict[str, str | None]:
    source = _compose_source_payload(enrollment_payload)

    resolved: dict[str, str | None] = {}
    for target_field, paths in mapping.items():
        value = None
        for path in paths:
            candidate = _coerce_clean(_deep_get(source, path))
            if candidate is not None:
                value = candidate
                break
        resolved[target_field] = value

    return resolved


def _flatten_payload(payload: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(_flatten_payload(value, path))
        elif isinstance(value, list):
            # Keep list payloads compact for preview labels.
            flattened[path] = _coerce_clean(value) or ""
        else:
            coerced = _coerce_clean(value)
            if coerced is not None:
                flattened[path] = coerced
    return flattened


def preview_student_metadata(canvas_course_id: str, limit: int = 10) -> dict[str, Any]:
    client = CanvasReadClient()
    if not client.configured:
        raise ValueError("Canvas credentials not configured")

    enrollments = client.fetch_enrollments(canvas_course_id)
    sampled = enrollments[: max(1, min(limit, 25))]

    label_samples: dict[str, list[str]] = {}
    row_samples: list[dict[str, Any]] = []

    for enrollment in sampled:
        source = _compose_source_payload(enrollment)
        flattened = _flatten_payload(source)

        row_samples.append(
            {
                "canvas_user_id": str((source.get("user") or {}).get("id") or source.get("user_id") or ""),
                "name": _coerce_clean((source.get("user") or {}).get("name")) or "Unknown",
                "sample_values": flattened,
            }
        )

        for path, value in flattened.items():
            samples = label_samples.setdefault(path, [])
            if value and value not in samples:
                samples.append(value)
            if len(samples) > 3:
                del samples[3:]

    label_summary = [
        {"source_path": path, "sample_values": values}
        for path, values in sorted(label_samples.items(), key=lambda item: item[0])
    ]

    return {
        "canvas_course_id": canvas_course_id,
        "sample_count": len(sampled),
        "labels": label_summary,
        "rows": row_samples,
    }
