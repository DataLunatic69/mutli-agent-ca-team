from sqlalchemy import String, ForeignKey, Date, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..db.base import Base


class ComplianceTask(Base):
    __tablename__ = "compliance_tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    due_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, in_progress, completed, cancelled
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, critical
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # filing, payment, documentation, review
    metadata: Mapped[JSON] = mapped_column(JSON, nullable=True)
    reminders_sent: Mapped[JSON] = mapped_column(JSON, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    related_doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship()
    assigned_to: Mapped["User"] = relationship()
    document: Mapped["Document"] = relationship()


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # tax, regulatory, internal
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, quarterly, annual, adhoc
    due_date_rule: Mapped[JSON] = mapped_column(JSON, nullable=False)  # JSON logic for calculating due dates
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    organization: Mapped["Organization"] = relationship()