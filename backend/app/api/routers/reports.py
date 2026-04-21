from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.reports import generate_student_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/students/{student_id}")
def create_student_report(student_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        paths = generate_student_report(db, student_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "student_id": student_id,
        "pdf_path": paths["pdf_path"],
        "png_path": paths["png_path"],
    }
