from sqlalchemy import String, ForeignKey, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from ..db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)  # PAN
    gstin: Mapped[str] = mapped_column(String(15), nullable=True, index=True)
    address: Mapped[JSON] = mapped_column(JSON, nullable=True)
    industry_code: Mapped[str] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    documents: Mapped[list["Document"]] = relationship(back_populates="organization")
    coas: Mapped[list["ChartOfAccounts"]] = relationship(back_populates="organization")
    ledgers: Mapped[list["LedgerEntry"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="users")