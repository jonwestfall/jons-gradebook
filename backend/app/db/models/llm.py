from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
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


class LLMRun(Base, TimestampMixin):
    __tablename__ = "llm_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[LLMProvider] = mapped_column(Enum(LLMProvider), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    input_text_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    deidentified_preview: Mapped[str] = mapped_column(Text, nullable=False)
    deidentify_map: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
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
