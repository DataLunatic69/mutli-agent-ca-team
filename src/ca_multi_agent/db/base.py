# src/ca_multi_agent/db/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
import uuid
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )


# Import all models here for Alembic to discover them
# This must be after the Base class definition
from ..models import user_org, document, accounting, reconciliation, tax, compliance, artifacts  # noqa