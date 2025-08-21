from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Generator

from ..db.session import AsyncSessionLocal, SyncSessionLocal

# For synchronous endpoints (most of our agents)
def get_db() -> Generator:
    """Get database session for synchronous operations"""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

# For asynchronous endpoints  
async def get_async_db() -> Generator:
    """Get database session for asynchronous operations"""
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

# Dependency for getting agents
def get_agent_dependency(agent_name: str):
    """Dependency to get agent instances with database session"""
    def _get_agent(db: Session = Depends(get_db)):
        from ..agents import get_agent
        return get_agent(agent_name, db)
    return _get_agent