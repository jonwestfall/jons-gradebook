from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Advisee, AdvisingMeeting, InteractionLog, InteractionType
from app.db.session import get_db
from app.schemas.advising import AdviseeCreate, AdvisingMeetingCreate

router = APIRouter(prefix="/advising", tags=["advising"])


@router.get("/advisees")
def list_advisees(db: Session = Depends(get_db)) -> list[dict]:
    advisees = db.scalars(select(Advisee).order_by(Advisee.last_name.asc(), Advisee.first_name.asc())).all()
    return [
        {
            "id": advisee.id,
            "student_profile_id": advisee.student_profile_id,
            "first_name": advisee.first_name,
            "last_name": advisee.last_name,
            "email": advisee.email,
            "external_id": advisee.external_id,
            "notes": advisee.notes,
        }
        for advisee in advisees
    ]


@router.post("/advisees")
def create_advisee(payload: AdviseeCreate, db: Session = Depends(get_db)) -> dict:
    advisee = Advisee(**payload.model_dump())
    db.add(advisee)
    db.commit()
    db.refresh(advisee)
    return {
        "id": advisee.id,
        "first_name": advisee.first_name,
        "last_name": advisee.last_name,
        "student_profile_id": advisee.student_profile_id,
    }


@router.get("/meetings")
def list_advising_meetings(db: Session = Depends(get_db)) -> list[dict]:
    meetings = db.scalars(select(AdvisingMeeting).order_by(AdvisingMeeting.meeting_at.desc())).all()
    return [
        {
            "id": meeting.id,
            "advisee_id": meeting.advisee_id,
            "meeting_at": meeting.meeting_at.isoformat(),
            "mode": meeting.mode.value,
            "summary": meeting.summary,
            "action_items": meeting.action_items,
        }
        for meeting in meetings
    ]


@router.post("/meetings")
def create_advising_meeting(payload: AdvisingMeetingCreate, db: Session = Depends(get_db)) -> dict:
    advisee = db.get(Advisee, payload.advisee_id)
    if not advisee:
        raise HTTPException(status_code=404, detail="Advisee not found")

    meeting = AdvisingMeeting(**payload.model_dump())
    db.add(meeting)
    db.flush()

    interaction = InteractionLog(
        student_profile_id=advisee.student_profile_id,
        advisee_id=advisee.id,
        interaction_type=InteractionType.advising_meeting,
        occurred_at=payload.meeting_at,
        summary=f"Advising meeting ({payload.mode.value})",
        notes=payload.summary,
        metadata_json={
            "advising_meeting_id": meeting.id,
            "action_items": payload.action_items,
        },
    )
    db.add(interaction)
    db.commit()
    db.refresh(meeting)
    return {
        "id": meeting.id,
        "advisee_id": meeting.advisee_id,
        "meeting_at": meeting.meeting_at.isoformat(),
        "mode": meeting.mode.value,
        "summary": meeting.summary,
    }
