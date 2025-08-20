from sqlalchemy import String, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)  # report, export, filing, summary
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, excel, json, csv
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[JSON] = mapped_column(JSON, nullable=True)
    size_bytes: Mapped[int] = mapped_column(nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generated_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    source_doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship()
    generated_by: Mapped["User"] = relationship()
    document: Mapped["Document"] = relationship()


class AgentRun(Base):
    __tablename__ = "agent_runs"

    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="started")  # started, completed, failed
    input_data: Mapped[JSON] = mapped_column(JSON, nullable=True)
    output_data: Mapped[JSON] = mapped_column(JSON, nullable=True)
    error_data: Mapped[JSON] = mapped_column(JSON, nullable=True)
    metrics: Mapped[JSON] = mapped_column(JSON, nullable=True)  # timings, token usage, etc.
    context: Mapped[JSON] = mapped_column(JSON, nullable=True)  # session context

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    parent_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship()
    parent_run: Mapped["AgentRun"] = relationship(remote_side="AgentRun.id")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    details: Mapped[JSON] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship()
    user: Mapped["User"] = relationship()