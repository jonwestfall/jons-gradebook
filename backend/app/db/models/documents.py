from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class DocumentType(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"
    other = "other"


class StoredDocument(Base, TimestampMixin):
    __tablename__ = "stored_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="Other")
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    versions = relationship("StoredDocumentVersion", back_populates="document", cascade="all, delete-orphan")
    student_links = relationship("StoredDocumentStudentLink", back_populates="document", cascade="all, delete-orphan")


class StoredDocumentVersion(Base, TimestampMixin):
    __tablename__ = "stored_document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number", name="uq_document_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("stored_documents.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    extracted_text_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    document = relationship("StoredDocument", back_populates="versions")


class StoredDocumentStudentLink(Base, TimestampMixin):
    __tablename__ = "stored_document_student_links"
    __table_args__ = (UniqueConstraint("document_id", "student_id", name="uq_document_student_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("stored_documents.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)

    document = relationship("StoredDocument", back_populates="student_links")
