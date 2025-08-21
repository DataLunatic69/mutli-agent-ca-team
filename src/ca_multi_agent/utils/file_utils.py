import os
import uuid
import magic
import hashlib
from typing import Optional, Tuple, BinaryIO
from pathlib import Path
import logging
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

class FileUtils:
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = upload_dir
        self.allowed_mime_types = {
            'application/pdf': 'pdf',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'text/csv': 'csv',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.ms-excel': 'xls'
        }
        self.max_file_size = 50 * 1024 * 1024  # 50MB

    async def save_upload_file(self, file: UploadFile) -> Tuple[str, str, str]:
        """Save uploaded file and return (file_id, file_path, sha256_hash)"""
        try:
            # Validate file size
            content = await file.read()
            if len(content) > self.max_file_size:
                raise HTTPException(400, f"File too large. Max size: {self.max_file_size/1024/1024}MB")
            
            # Validate file type
            mime_type = magic.from_buffer(content, mime=True)
            if mime_type not in self.allowed_mime_types:
                raise HTTPException(400, f"Unsupported file type: {mime_type}")
            
            # Generate file ID and path
            file_id = str(uuid.uuid4())
            extension = self.allowed_mime_types[mime_type]
            filename = f"{file_id}.{extension}"
            file_path = os.path.join(self.upload_dir, filename)
            
            # Create upload directory if it doesn't exist
            os.makedirs(self.upload_dir, exist_ok=True)
            
            # Calculate SHA256 hash
            sha256_hash = hashlib.sha256(content).hexdigest()
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"File saved: {filename}, size: {len(content)} bytes, hash: {sha256_hash}")
            
            return file_id, file_path, sha256_hash
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise HTTPException(500, f"File upload failed: {str(e)}")

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get file information"""
        if not os.path.exists(file_path):
            return None
            
        return {
            'size': os.path.getsize(file_path),
            'modified_time': os.path.getmtime(file_path),
            'extension': Path(file_path).suffix.lower(),
            'exists': True
        }

    def validate_file_path(self, file_path: str) -> bool:
        """Validate that file path is within allowed directory"""
        try:
            absolute_path = os.path.abspath(file_path)
            absolute_upload_dir = os.path.abspath(self.upload_dir)
            return absolute_path.startswith(absolute_upload_dir)
        except:
            return False

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up files older than specified hours"""
        try:
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    file_age = (time.time() - os.path.getmtime(file_path)) / 3600
                    if file_age > max_age_hours:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")

    def get_file_content(self, file_path: str, max_size: int = None) -> Optional[bytes]:
        """Read file content with size limit"""
        if not self.validate_file_path(file_path):
            return None
            
        try:
            with open(file_path, "rb") as f:
                if max_size:
                    content = f.read(max_size)
                else:
                    content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None

# Global instance
file_utils = FileUtils()