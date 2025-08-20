# src/ca_multi_agent/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from ..config.settings import settings

# Use the same URL for both sync and async. SQLAlchemy handles the async adaptation.
# The 'psycopg' driver (used by psycopg2-binary) supports async in SQLAlchemy.
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    str(settings.DATABASE_URL).replace("+psycopg2", ""), # Alembic uses sync driver
    echo=settings.DEBUG,
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Sync session factory (for Alembic, scripts)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
)