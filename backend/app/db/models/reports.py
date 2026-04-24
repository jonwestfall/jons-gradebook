from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class ReportTemplate(Base, TimestampMixin):
    __tablename__ = "report_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    report_type: Mapped[str] = mapped_column(String(60), nullable=False, default="student")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    assets = relationship("ReportTemplateAsset", back_populates="template", cascade="all, delete-orphan")
    runs = relationship("ReportRun", back_populates="template")


class ReportTemplateAsset(Base, TimestampMixin):
    __tablename__ = "report_template_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("report_templates.id", ondelete="CASCADE"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    template = relationship("ReportTemplate", back_populates="assets")


class ReportRun(Base, TimestampMixin):
    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("report_templates.id", ondelete="SET NULL"))
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(60), nullable=False, default="student")
    filters_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    pdf_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    png_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    pdf_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stored_documents.id", ondelete="SET NULL"))
    png_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stored_documents.id", ondelete="SET NULL"))

    template = relationship("ReportTemplate", back_populates="runs")
    student = relationship("StudentProfile")
