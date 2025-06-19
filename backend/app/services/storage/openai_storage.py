"""
OpenAI Files API Storage Service
Handles file uploads to OpenAI with database tracking for management
"""
from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, update
import io
import logging
from datetime import datetime

from app.core.config import settings
from app.models.database.openai_file import OpenAIFile
from app.integrations.openai.error_handler import handle_openai_errors

logger = logging.getLogger(__name__)

class OpenAIStorageService:
    """
    OpenAI Files API Service with Database Tracking
    
    Features:
    - Upload files to OpenAI Files API
    - Track all uploads in database 
    - List files by user/purpose
    - Bulk delete files
    - Cost tracking integration
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.logger = logger
    
    def _validate_file(self, file_data: bytes, filename: str, purpose: str):
        """Validate against OpenAI requirements only"""
        
        # Check file size (OpenAI limit: 512MB)
        if len(file_data) > settings.OPENAI_FILES_MAX_SIZE:
            raise ValueError(f"File too large. Max: 512MB")
        
        # Check purpose
        valid_purposes = ["vision", "assistants", "fine-tune"]
        if purpose not in valid_purposes:
            raise ValueError(f"Invalid purpose. Must be: {valid_purposes}")
        
        # Check file extension for purpose
        ext = filename.split('.')[-1].lower() if '.' in filename else ""
        
        if purpose == "vision" and ext not in ["png", "jpg", "jpeg", "gif", "webp"]:
            raise ValueError(f"Unsupported format for vision: {ext}")
        
        if purpose == "fine-tune" and ext != "jsonl":
            raise ValueError(f"Fine-tune only supports .jsonl files")
    
    @handle_openai_errors(max_retries=3)
    async def upload_file(
        self, 
        file_data: bytes,
        filename: str,
        purpose: str = "vision",
        user_id: str = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Upload file with database tracking"""
        
        # Validate against OpenAI requirements
        self._validate_file(file_data, filename, purpose)
        
        try:
            # Create file-like object
            file_obj = io.BytesIO(file_data)
            file_obj.name = filename
            
            # Upload to OpenAI
            result = await self.client.files.create(
                file=file_obj,
                purpose=purpose
            )
            
            # Store in database if session provided
            if db and user_id:
                openai_file = OpenAIFile(
                    openai_file_id=result.id,
                    filename=result.filename,
                    purpose=result.purpose,
                    user_id=user_id,
                    file_size_bytes=result.bytes,
                    status=result.status or "uploaded"
                )
                
                db.add(openai_file)
                await db.commit()
                await db.refresh(openai_file)
                
                self.logger.info(f"OpenAI file uploaded and tracked: {result.id} for user {user_id}")
            
            return {
                "openai_file_id": result.id,
                "filename": result.filename,
                "purpose": result.purpose,
                "size_bytes": result.bytes,
                "status": result.status,
                "created_at": datetime.fromtimestamp(result.created_at).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"OpenAI upload failed: {e}")
            raise
    
    @handle_openai_errors(max_retries=3)
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata from OpenAI"""
        try:
            result = await self.client.files.retrieve(file_id)
            return {
                "openai_file_id": result.id,
                "filename": result.filename,
                "purpose": result.purpose,
                "size_bytes": result.bytes,
                "status": result.status,
                "created_at": datetime.fromtimestamp(result.created_at).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get file info: {e}")
            raise
    
    @handle_openai_errors(max_retries=3)
    async def delete_file(self, file_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete file from OpenAI and database"""
        try:
            # Delete from OpenAI
            await self.client.files.delete(file_id)
            
            # Remove from database if session provided
            if db:
                stmt = delete(OpenAIFile).where(OpenAIFile.openai_file_id == file_id)
                await db.execute(stmt)
                await db.commit()
                
            self.logger.info(f"OpenAI file deleted: {file_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Delete failed: {e}")
            return False
    
    async def list_user_files(
        self, 
        user_id: str, 
        db: AsyncSession,
        purpose: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files uploaded by user"""
        
        query = select(OpenAIFile).where(OpenAIFile.user_id == user_id)
        
        if purpose:
            query = query.where(OpenAIFile.purpose == purpose)
        
        query = query.order_by(desc(OpenAIFile.uploaded_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        files = result.scalars().all()
        
        return [file.to_dict() for file in files]
    
    async def list_all_files(
        self, 
        db: AsyncSession,
        purpose: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List all tracked files"""
        
        query = select(OpenAIFile)
        
        if purpose:
            query = query.where(OpenAIFile.purpose == purpose)
        
        query = query.order_by(desc(OpenAIFile.uploaded_at)).limit(limit).offset(offset)
        
        result = await db.execute(query)
        files = result.scalars().all()
        
        return [file.to_dict() for file in files]
    
    @handle_openai_errors(max_retries=3)
    async def bulk_delete_user_files(
        self, 
        user_id: str, 
        db: AsyncSession,
        purpose: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete all files for a user"""
        
        # Get files to delete
        query = select(OpenAIFile).where(OpenAIFile.user_id == user_id)
        if purpose:
            query = query.where(OpenAIFile.purpose == purpose)
        
        result = await db.execute(query)
        files = result.scalars().all()
        
        deleted_count = 0
        failed_files = []
        
        for file in files:
            try:
                # Delete from OpenAI
                await self.client.files.delete(file.openai_file_id)
                deleted_count += 1
            except Exception as e:
                failed_files.append({
                    "file_id": file.openai_file_id,
                    "error": str(e)
                })
        
        # Remove from database
        delete_stmt = delete(OpenAIFile).where(OpenAIFile.user_id == user_id)
        if purpose:
            delete_stmt = delete_stmt.where(OpenAIFile.purpose == purpose)
        
        await db.execute(delete_stmt)
        await db.commit()
        
        return {
            "total_files": len(files),
            "deleted_count": deleted_count,
            "failed_count": len(failed_files),
            "failed_files": failed_files
        }
    
    async def update_last_used(self, file_id: str, db: AsyncSession):
        """Update last used timestamp when file is used in chat"""
        try:
            stmt = select(OpenAIFile).where(OpenAIFile.openai_file_id == file_id)
            result = await db.execute(stmt)
            file_record = result.scalar_one_or_none()
            
            if file_record:
                # Update the datetime field properly
                update_stmt = update(OpenAIFile).where(
                    OpenAIFile.openai_file_id == file_id
                ).values(last_used_at=datetime.utcnow())
                
                await db.execute(update_stmt)
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update last used: {e}")

# Global instance
openai_storage_service = OpenAIStorageService()
