from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def health_check():
    return {"status": "healthy", "service": "CA Multi-Agent API"}