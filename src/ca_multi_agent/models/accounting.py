from sqlalchemy import String, ForeignKey, Numeric, Date, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..db.base import Base


class ChartOfAccounts(Base):
    __tablename__ = "chart_of_accounts"

    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # Asset, Liability, Income, Expense, Equity
    parent_code: Mapped[str] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[JSON] = mapped_column(JSON, nullable=True)  # GST, TDS, Depreciation, etc.

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="coas")
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="account")


class Voucher(Base):
    __tablename__ = "vouchers"

    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # Payment, Receipt, Journal, Contra
    ref_no: Mapped[str] = mapped_column(String(100), nullable=True)
    narration: Mapped[str] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=True)  # manual, import, agent
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="posted")  # draft, posted, cancelled

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="vouchers")
    document: Mapped["Document"] = relationship()
    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="voucher", cascade="all, delete-orphan")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    account_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    party: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    debit: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0)
    credit: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0)
    balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    tags: Mapped[JSON] = mapped_column(JSON, nullable=True)

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    voucher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vouchers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    doc_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="ledgers")
    voucher: Mapped["Voucher"] = relationship(back_populates="entries")
    account: Mapped["ChartOfAccounts"] = relationship(back_populates="ledger_entries")
    document: Mapped["Document"] = relationship()