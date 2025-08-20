from sqlalchemy import String, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from ..db.base import Base


class Document(Base):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=True)  # invoice, bank_statement, form_26as, etc.

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="documents")
    pages: Mapped[list["DocPage"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    embeddings: Mapped[list["Embedding"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocPage(Base):
    __tablename__ = "doc_pages"

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_tables: Mapped[JSON] = mapped_column(JSON, nullable=True)
    entities: Mapped[JSON] = mapped_column(JSON, nullable=True)  # NER results

    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    document: Mapped["Document"] = relationship(back_populates="pages")


class Embedding(Base):
    __tablename__ = "embeddings"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column("embedding", JSON, nullable=True)  # For pgvector compatibility
    meta: Mapped[JSON] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # document, page, transaction
    source_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    document: Mapped["Document"] = relationship(back_populates="embeddings")