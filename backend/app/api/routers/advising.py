from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Advisee, AdvisingMeeting, InteractionLog, InteractionType
from app.db.session import get_db
from app.schemas.advising import AdviseeCreate, AdvisingMeetingCreate

router = APIRouter(prefix="/advising", tags=["advising"])


@router.get("/advisees")
def list_advisees(db: Session = Depends(get_db)) -> list[dict]:
    advisees = db.scalars(select(Advisee).order_by(Advisee.last_name.asc(), Advisee.first_name.asc())).all()
    if not advisees:
        return []

    advisee_ids = [advisee.id for advisee in advisees]
    profile_to_advisee_ids: dict[int, list[int]] = {}
    for advisee in advisees:
        if advisee.student_profile_id is not None:
            profile_to_advisee_ids.setdefault(advisee.student_profile_id, []).append(advisee.id)

    meeting_count_map = {advisee_id: 0 for advisee_id in advisee_ids}
    latest_meeting_map: dict[int, object | None] = {advisee_id: None for advisee_id in advisee_ids}

    meeting_rows = db.execute(
        select(
            AdvisingMeeting.advisee_id,
            func.count(AdvisingMeeting.id),
            func.max(AdvisingMeeting.meeting_at),
        )
        .where(AdvisingMeeting.advisee_id.in_(advisee_ids))
        .group_by(AdvisingMeeting.advisee_id)
    ).all()
    for advisee_id, count, latest in meeting_rows:
        meeting_count_map[advisee_id] = int(count or 0)
        latest_meeting_map[advisee_id] = latest

    profile_ids = list(profile_to_advisee_ids.keys())
    office_visit_rows = (
        db.scalars(
            select(InteractionLog).where(
                InteractionLog.interaction_type == InteractionType.office_visit,
                or_(
                    InteractionLog.advisee_id.in_(advisee_ids),
                    InteractionLog.student_profile_id.in_(profile_ids) if profile_ids else False,
                ),
            )
        ).all()
        if advisee_ids
        else []
    )

    for interaction in office_visit_rows:
        targets: set[int] = set()
        if interaction.advisee_id is not None:
            targets.add(interaction.advisee_id)
        if interaction.student_profile_id is not None:
            targets.update(profile_to_advisee_ids.get(interaction.student_profile_id, []))
        for advisee_id in targets:
            meeting_count_map[advisee_id] = meeting_count_map.get(advisee_id, 0) + 1
            current_latest = latest_meeting_map.get(advisee_id)
            if current_latest is None or interaction.occurred_at > current_latest:
                latest_meeting_map[advisee_id] = interaction.occurred_at

    return [
        {
            "id": advisee.id,
            "student_profile_id": advisee.student_profile_id,
            "first_name": advisee.first_name,
            "last_name": advisee.last_name,
            "email": advisee.email,
            "external_id": advisee.external_id,
            "notes": advisee.notes,
            "latest_meeting_at": latest_meeting_map[advisee.id].isoformat() if latest_meeting_map[advisee.id] else None,
            "meeting_count": int(meeting_count_map[advisee.id]),
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
def list_advising_meetings(
    advisee_id: int | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(AdvisingMeeting).order_by(AdvisingMeeting.meeting_at.desc())
    if advisee_id is not None:
        query = query.where(AdvisingMeeting.advisee_id == advisee_id)

    meetings = db.scalars(query.limit(limit)).all()
    if not meetings:
        return []

    advisee_ids = sorted({meeting.advisee_id for meeting in meetings})
    advisees = db.scalars(select(Advisee).where(Advisee.id.in_(advisee_ids))).all()
    advisee_map = {advisee.id: advisee for advisee in advisees}

    return [
        {
            "id": meeting.id,
            "advisee_id": meeting.advisee_id,
            "meeting_at": meeting.meeting_at.isoformat(),
            "mode": meeting.mode.value,
            "summary": meeting.summary,
            "action_items": meeting.action_items,
            "advisee_name": (
                f"{advisee_map[meeting.advisee_id].first_name} {advisee_map[meeting.advisee_id].last_name}".strip()
                if meeting.advisee_id in advisee_map
                else None
            ),
            "student_profile_id": advisee_map[meeting.advisee_id].student_profile_id if meeting.advisee_id in advisee_map else None,
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
        "action_items": meeting.action_items,
        "advisee_name": f"{advisee.first_name} {advisee.last_name}".strip(),
        "student_profile_id": advisee.student_profile_id,
    }
