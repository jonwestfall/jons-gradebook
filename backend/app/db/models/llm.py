from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class LLMProvider(str, enum.Enum):
    openai = "openai"
    ollama = "ollama"
    gemini = "gemini"


class LLMRunStatus(str, enum.Enum):
    draft = "draft"
    previewed = "previewed"
    sent = "sent"
    completed = "completed"
    failed = "failed"


class LLMWorkbenchJobStatus(str, enum.Enum):
    draft = "draft"
    prompt_ready = "prompt_ready"
    output_ready = "output_ready"
    final_ready = "final_ready"
    finalized = "finalized"
    failed = "failed"


class LLMInstructionTemplate(Base, TimestampMixin):
    __tablename__ = "llm_instruction_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False, default="feedback")
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    output_guidance: Mapped[Optional[str]] = mapped_column(Text)
    rubric_guidance: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class LLMRun(Base, TimestampMixin):
    __tablename__ = "llm_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[LLMProvider] = mapped_column(Enum(LLMProvider), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    input_text_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    deidentified_preview: Mapped[str] = mapped_column(Text, nullable=False)
    deidentify_map: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    deidentify_map_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[LLMRunStatus] = mapped_column(Enum(LLMRunStatus), nullable=False, default=LLMRunStatus.draft)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    outputs = relationship("LLMOutput", back_populates="run", cascade="all, delete-orphan")


class LLMOutput(Base, TimestampMixin):
    __tablename__ = "llm_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("llm_runs.id", ondelete="CASCADE"), nullable=False)
    output_text_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    edited_text_encrypted: Mapped[Optional[str]] = mapped_column(Text)

    run = relationship("LLMRun", back_populates="outputs")


class LLMWorkbenchJob(Base, TimestampMixin):
    __tablename__ = "llm_workbench_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("stored_documents.id", ondelete="CASCADE"), nullable=False)
    instruction_template_id: Mapped[int] = mapped_column(ForeignKey("llm_instruction_templates.id", ondelete="RESTRICT"), nullable=False)
    rubric_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rubric_templates.id", ondelete="SET NULL"))
    llm_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("llm_runs.id", ondelete="SET NULL"))
    final_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stored_documents.id", ondelete="SET NULL"))
    provider: Mapped[LLMProvider] = mapped_column(Enum(LLMProvider), nullable=False, default=LLMProvider.ollama)
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="llama3.1")
    status: Mapped[LLMWorkbenchJobStatus] = mapped_column(
        Enum(LLMWorkbenchJobStatus), nullable=False, default=LLMWorkbenchJobStatus.draft
    )
    final_feedback_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    student = relationship("StudentProfile")
    source_document = relationship("StoredDocument", foreign_keys=[source_document_id])
    instruction_template = relationship("LLMInstructionTemplate")
    rubric = relationship("RubricTemplate")
    llm_run = relationship("LLMRun")
    final_document = relationship("StoredDocument", foreign_keys=[final_document_id])
