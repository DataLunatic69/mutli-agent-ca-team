from sqlalchemy import String, ForeignKey, Numeric, Date, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..db.base import Base


class GSTReturn(Base):
    __tablename__ = "gst_returns"

    return_period: Mapped[str] = mapped_column(String(20), nullable=False)  # MM-YYYY
    return_type: Mapped[str] = mapped_column(String(10), nullable=False)  # GSTR1, GSTR3B, GSTR9
    gstin: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, filed, submitted, approved
    filing_date: Mapped[Date] = mapped_column(Date, nullable=True)
    arn: Mapped[str] = mapped_column(String(50), nullable=True)  # Application Reference Number
    payload: Mapped[JSON] = mapped_column(JSON, nullable=True)
    summary: Mapped[JSON] = mapped_column(JSON, nullable=True)
    liabilities: Mapped[JSON] = mapped_column(JSON, nullable=True)
    itc_details: Mapped[JSON] = mapped_column(JSON, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    organization: Mapped["Organization"] = relationship()


class ITReturn(Base):
    __tablename__ = "it_returns"

    assessment_year: Mapped[str] = mapped_column(String(10), nullable=False)  # 2024-25
    return_type: Mapped[str] = mapped_column(String(10), nullable=False)  # ITR1, ITR2, ITR3, ITR4
    pan: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, filed, submitted, processed
    filing_date: Mapped[Date] = mapped_column(Date, nullable=True)
    ack_number: Mapped[str] = mapped_column(String(50), nullable=True)
    payload: Mapped[JSON] = mapped_column(JSON, nullable=True)
    computation: Mapped[JSON] = mapped_column(JSON, nullable=True)
    tax_paid: Mapped[JSON] = mapped_column(JSON, nullable=True)
    tds_tcs: Mapped[JSON] = mapped_column(JSON, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    organization: Mapped["Organization"] = relationship()


class TaxComputation(Base):
    __tablename__ = "tax_computations"

    financial_year: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)  # income_tax, gst, tds, tcs
    computation_data: Mapped[JSON] = mapped_column(JSON, nullable=False)
    result: Mapped[JSON] = mapped_column(JSON, nullable=False)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship()
    document: Mapped["Document"] = relationship()