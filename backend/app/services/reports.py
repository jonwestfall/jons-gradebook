from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.db.models import AttendanceRecord, Enrollment, InteractionLog, StudentProfile


BRAND_TITLE = "Jon's Gradebook"


def _student_summary(db: Session, student_id: int) -> dict:
    student = db.scalar(
        select(StudentProfile)
        .where(StudentProfile.id == student_id)
        .options(joinedload(StudentProfile.enrollments).joinedload(Enrollment.course))
    )
    if not student:
        raise ValueError("Student not found")

    attendance_rows = db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id == student_id)).all()
    attendance_counts = Counter(record.status.value for record in attendance_rows)

    interaction_rows = db.scalars(
        select(InteractionLog).where(InteractionLog.student_profile_id == student_id).order_by(InteractionLog.occurred_at.desc())
    ).all()

    return {
        "student": student,
        "courses": [enrollment.course.name for enrollment in student.enrollments],
        "attendance": dict(attendance_counts),
        "recent_interactions": [
            {
                "type": interaction.interaction_type.value,
                "summary": interaction.summary,
                "occurred_at": interaction.occurred_at.isoformat(),
            }
            for interaction in interaction_rows[:10]
        ],
    }


def _draw_pdf(report_path: Path, summary: dict) -> None:
    pdf = canvas.Canvas(str(report_path), pagesize=LETTER)
    width, height = LETTER

    student = summary["student"]

    y = height - 60
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, f"{BRAND_TITLE} - Student Report")

    y -= 30
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Student: {student.first_name} {student.last_name}")
    y -= 18
    pdf.drawString(50, y, f"Email: {student.email or 'N/A'}")
    y -= 18
    pdf.drawString(50, y, "Courses: " + (", ".join(summary["courses"]) or "None"))

    y -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Attendance")
    y -= 18
    pdf.setFont("Helvetica", 11)
    for status in ("present", "absent", "tardy", "excused"):
        pdf.drawString(60, y, f"{status.title()}: {summary['attendance'].get(status, 0)}")
        y -= 16

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Recent Interactions")
    y -= 18
    pdf.setFont("Helvetica", 10)

    for interaction in summary["recent_interactions"][:8]:
        line = f"- {interaction['occurred_at'][:10]} [{interaction['type']}] {interaction['summary']}"
        pdf.drawString(60, y, line[:110])
        y -= 14
        if y < 70:
            pdf.showPage()
            y = height - 60

    pdf.save()


def _draw_png(image_path: Path, summary: dict) -> None:
    image = Image.new("RGB", (1200, 1600), "#f5f7fb")
    draw = ImageDraw.Draw(image)
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()

    student = summary["student"]

    y = 40
    draw.text((40, y), f"{BRAND_TITLE} - Student Report", fill="#1b2840", font=font_title)
    y += 50
    draw.text((40, y), f"Student: {student.first_name} {student.last_name}", fill="#14213d", font=font_body)
    y += 24
    draw.text((40, y), f"Email: {student.email or 'N/A'}", fill="#14213d", font=font_body)
    y += 24
    draw.text((40, y), "Courses: " + (", ".join(summary["courses"]) or "None"), fill="#14213d", font=font_body)

    y += 40
    draw.text((40, y), "Attendance", fill="#1b2840", font=font_title)
    y += 26
    for status in ("present", "absent", "tardy", "excused"):
        draw.text((50, y), f"{status.title()}: {summary['attendance'].get(status, 0)}", fill="#27314f", font=font_body)
        y += 20

    y += 16
    draw.text((40, y), "Recent Interactions", fill="#1b2840", font=font_title)
    y += 26

    for interaction in summary["recent_interactions"][:15]:
        line = f"{interaction['occurred_at'][:10]} [{interaction['type']}] {interaction['summary']}"
        draw.text((50, y), line[:140], fill="#27314f", font=font_body)
        y += 20

    image.save(image_path, format="PNG")


def generate_student_report(db: Session, student_id: int) -> dict[str, str]:
    settings = get_settings()
    output_root = Path(settings.storage_root) / "reports" / str(student_id)
    output_root.mkdir(parents=True, exist_ok=True)

    summary = _student_summary(db, student_id)

    pdf_path = output_root / "student-report.pdf"
    png_path = output_root / "student-report.png"

    _draw_pdf(pdf_path, summary)
    _draw_png(png_path, summary)

    return {
        "pdf_path": str(pdf_path),
        "png_path": str(png_path),
    }
