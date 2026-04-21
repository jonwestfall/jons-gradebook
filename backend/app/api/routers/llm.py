from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LLMRun
from app.db.session import get_db
from app.schemas.llm import LLMOutputEditRequest, LLMPreviewRequest
from app.services.llm.service import create_preview_run, get_run_with_output, send_run, update_output_text

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/preview")
def preview_run(payload: LLMPreviewRequest, db: Session = Depends(get_db)) -> dict:
    run = create_preview_run(db, provider=payload.provider, model=payload.model, prompt=payload.prompt)
    return {
        "run_id": run.id,
        "provider": run.provider.value,
        "model": run.model,
        "status": run.status.value,
        "preview": run.deidentified_preview,
        "deidentify_map": run.deidentify_map,
    }


@router.post("/runs/{run_id}/send")
def send_previewed_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        output = send_run(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "output_id": output.id,
        "run_id": output.run_id,
        "message": "LLM output generated and stored",
    }


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(LLMRun).order_by(LLMRun.created_at.desc())).all()
    return [
        {
            "id": run.id,
            "provider": run.provider.value,
            "model": run.model,
            "status": run.status.value,
            "created_at": run.created_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
        for run in runs
    ]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return get_run_with_output(db, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/outputs/{output_id}")
def edit_output(output_id: int, payload: LLMOutputEditRequest, db: Session = Depends(get_db)) -> dict:
    try:
        output = update_output_text(db, output_id, payload.edited_text)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "output_id": output.id,
        "run_id": output.run_id,
        "message": "Edited output stored",
    }
