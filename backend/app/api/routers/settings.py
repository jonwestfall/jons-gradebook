from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppOption
from app.db.session import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_DOCUMENT_CATEGORIES = ["Record", "Assignment", "Note", "Other"]
DEFAULT_INTERACTION_CATEGORIES = [
    "Manual Note",
    "Office Visit",
    "Email Log",
    "Attendance",
    "File Upload",
    "Advising Meeting",
]
DEFAULT_INTERVENTION_RULES = [
    {
        "name": "missing-and-low-grade",
        "min_score": 60,
        "priority": "high",
        "due_days": 2,
        "template": "Follow up with student on missing work and recovery plan.",
    }
]

OPTION_DEFAULTS = {
    "document_categories": DEFAULT_DOCUMENT_CATEGORIES,
    "interaction_categories": DEFAULT_INTERACTION_CATEGORIES,
    "intervention_rules": DEFAULT_INTERVENTION_RULES,
}


def _normalize_list(values: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for value in values:
        token = str(value).strip()
        if not token:
            continue
        lowered = token.lower()
        if lowered in seen:
            continue
        cleaned.append(token)
        seen.add(lowered)
    return cleaned


@router.get("/options")
def list_settings_options(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(AppOption).where(AppOption.key.in_(OPTION_DEFAULTS.keys()))).all()
    by_key = {row.key: row.value_json for row in rows}
    return {
        "document_categories": by_key.get("document_categories", DEFAULT_DOCUMENT_CATEGORIES),
        "interaction_categories": by_key.get("interaction_categories", DEFAULT_INTERACTION_CATEGORIES),
        "intervention_rules": by_key.get("intervention_rules", DEFAULT_INTERVENTION_RULES),
    }


@router.put("/options/{key}")
def update_settings_option(key: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    if key not in OPTION_DEFAULTS:
        raise HTTPException(status_code=404, detail="Unsupported settings option key")

    row = db.scalar(select(AppOption).where(AppOption.key == key))

    if key == "intervention_rules":
        values = payload.get("values")
        if not isinstance(values, list):
            raise HTTPException(status_code=400, detail="values must be a list")
        normalized = values or OPTION_DEFAULTS[key]
    else:
        values = payload.get("values")
        if not isinstance(values, list):
            raise HTTPException(status_code=400, detail="values must be a list of strings")

        normalized = _normalize_list([str(item) for item in values])
        if not normalized:
            normalized = OPTION_DEFAULTS[key]

    if not row:
        row = AppOption(key=key, value_json=normalized)
        db.add(row)
    else:
        row.value_json = normalized

    db.commit()
    db.refresh(row)
    return {
        "key": row.key,
        "values": row.value_json,
    }
