from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InteractionLog
from app.db.session import get_db
from app.schemas.interactions import InteractionCreate

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/")
def list_interactions(db: Session = Depends(get_db)) -> list[dict]:
    interactions = db.scalars(select(InteractionLog).order_by(InteractionLog.occurred_at.desc()).limit(200)).all()
    return [
        {
            "id": interaction.id,
            "student_profile_id": interaction.student_profile_id,
            "advisee_id": interaction.advisee_id,
            "interaction_type": interaction.interaction_type.value,
            "occurred_at": interaction.occurred_at.isoformat(),
            "summary": interaction.summary,
            "notes": interaction.notes,
            "metadata": interaction.metadata_json,
        }
        for interaction in interactions
    ]


@router.post("/")
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)) -> dict:
    interaction = InteractionLog(**payload.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return {
        "id": interaction.id,
        "interaction_type": interaction.interaction_type.value,
        "occurred_at": interaction.occurred_at.isoformat(),
    }
