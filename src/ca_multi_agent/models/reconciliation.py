from sqlalchemy import String, ForeignKey, Numeric, Date, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from ..db.base import Base


class BankStatement(Base):
    __tablename__ = "bank_statements"

    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=True)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    opening_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    closing_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # upload, api
    raw_data: Mapped[JSON] = mapped_column(JSON, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )

    organization: Mapped["Organization"] = relationship()
    document: Mapped["Document"] = relationship()
    transactions: Mapped[list["BankTransaction"]] = relationship(back_populates="statement", cascade="all, delete-orphan")
    reconciliations: Mapped[list["Reconciliation"]] = relationship(back_populates="bank_statement")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[Date] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str] = mapped_column(String(100), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # debit, credit
    balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)

    statement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False, index=True
    )

    statement: Mapped["BankStatement"] = relationship(back_populates="transactions")
    matches: Mapped[list["ReconciliationMatch"]] = relationship(back_populates="bank_transaction")


class Reconciliation(Base):
    __tablename__ = "reconciliations"

    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, in_progress, completed, error
    summary: Mapped[JSON] = mapped_column(JSON, nullable=True)
    settings: Mapped[JSON] = mapped_column(JSON, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_statement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False
    )

    organization: Mapped["Organization"] = relationship()
    bank_statement: Mapped["BankStatement"] = relationship(back_populates="reconciliations")
    matches: Mapped[list["ReconciliationMatch"]] = relationship(back_populates="reconciliation", cascade="all, delete-orphan")


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    match_type: Mapped[str] = mapped_column(String(20), nullable=False)  # exact, partial, manual, unmatched
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=True)  # 0.0 to 1.0
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reconciliations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=False
    )
    ledger_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ledger_entries.id", ondelete="CASCADE"), nullable=True
    )

    reconciliation: Mapped["Reconciliation"] = relationship(back_populates="matches")
    bank_transaction: Mapped["BankTransaction"] = relationship(back_populates="matches")
    ledger_entry: Mapped["LedgerEntry"] = relationship()