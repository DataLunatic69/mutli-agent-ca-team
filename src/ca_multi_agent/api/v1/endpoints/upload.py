from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import uuid
import shutil
import os
from src.ca_multi_agent.config.settings import settings

router = APIRouter()

class UploadResponse(BaseModel):
    file_id: uuid.UUID
    filename: str
    message: str

@router.post("")
async def upload_file(file: UploadFile = File(...)):
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    file_path = f"{settings.UPLOAD_DIR}/{file_id}{file_extension}"
    
    try:
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # TODO: Store file metadata in database
        # TODO: Trigger document ingestion agent
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            message="File uploaded successfully. Processing will begin shortly."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")