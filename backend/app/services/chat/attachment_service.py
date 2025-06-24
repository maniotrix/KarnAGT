"""
Attachment Service for Chat Message Integration
Optimized to use known S3 keys from staging upload - no more guessing!
"""

from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.storage.staging_storage import staging_service

from aicore.logger import get_logger

logger = get_logger(__name__)


class AttachmentService:
    """Service for managing message attachments with optimized direct key access"""
    
    async def commit_staging_files_direct(
        self, 
        staging_files: List[Dict[str, str]], 
        user_id: str, 
        db: AsyncSession
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Commit staging files using known file_id and s3_key pairs (optimized!)
        
        Args:
            staging_files: List of dicts with file_id and s3_key pairs
                          [{"file_id": "img_abc123", "s3_key": "images/2024/01/15/img_abc123.jpg"}, ...]
            user_id: User ID for validation
            db: Database session
            
        Returns:
            Tuple of (message_attachments, openai_file_ids)
            - message_attachments: List of attachment data for database storage
            - openai_file_ids: List of OpenAI file IDs for LLM context
        """
        logger.info(f"Committing {len(staging_files)} staging files with known keys")
        
        if not staging_files:
            return [], []
        
        # Validate staging files format
        validation_result = await self.validate_staging_files_format(staging_files)
        if not validation_result["valid"]:
            raise ValueError(f"Staging files validation failed: {validation_result['errors']}")
        
        # Commit staging files using known S3 keys (no guessing!)
        commit_result = await staging_service.commit_files_with_known_keys(
            staging_files=staging_files,
            user_id=user_id,
            db=db
        )
        
        if commit_result["failed_commits"] > 0:
            logger.warning(f"Some files failed to commit: {commit_result['failed_files']}")
        
        if commit_result["successfully_committed"] == 0:
            raise ValueError("No files were successfully committed")
        
        # Extract message attachments and OpenAI file IDs
        message_attachments = commit_result["message_attachments"]
        openai_file_ids = [attachment["openai_file_id"] for attachment in message_attachments]
        
        logger.info(f"Successfully committed {len(message_attachments)} files, got {len(openai_file_ids)} OpenAI file IDs")
        
        return message_attachments, openai_file_ids
    
    async def get_openai_file_ids_from_attachments(
        self, 
        attachments: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract OpenAI file IDs from message attachments for context building
        
        Args:
            attachments: List of message attachment dictionaries
            
        Returns:
            List of OpenAI file IDs
        """
        if not attachments:
            return []
        
        openai_file_ids = []
        for attachment in attachments:
            if isinstance(attachment, dict) and "openai_file_id" in attachment:
                openai_file_ids.append(attachment["openai_file_id"])
        
        logger.debug(f"Extracted {len(openai_file_ids)} OpenAI file IDs from {len(attachments)} attachments")
        return openai_file_ids
    
    async def validate_staging_files_format(
        self, 
        staging_files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Validate staging files format (file_id and s3_key pairs)
        
        Args:
            staging_files: List of staging file dictionaries
            
        Returns:
            Dict with validation results
        """
        logger.info(f"Validating format of {len(staging_files)} staging files")
        
        if not staging_files:
            return {"valid": True, "errors": [], "validated_files": []}
        
        errors = []
        validated_files = []
        
        for i, staging_file in enumerate(staging_files):
            try:
                # Validate required fields
                if not isinstance(staging_file, dict):
                    errors.append(f"File {i}: Must be a dictionary")
                    continue
                
                file_id = staging_file.get("file_id")
                s3_key = staging_file.get("s3_key")
                
                if not file_id:
                    errors.append(f"File {i}: Missing file_id")
                    continue
                    
                if not s3_key:
                    errors.append(f"File {i}: Missing s3_key")
                    continue
                
                # Validate file_id format
                if not file_id.startswith("img_"):
                    errors.append(f"File {i}: Invalid file_id format (must start with 'img_')")
                    continue
                
                # Validate s3_key format
                if not s3_key.startswith("images/"):
                    errors.append(f"File {i}: Invalid s3_key format (must start with 'images/')")
                    continue
                
                validated_files.append({
                    "file_id": file_id,
                    "s3_key": s3_key
                })
                
            except Exception as e:
                errors.append(f"Error validating file {i}: {str(e)}")
        
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "validated_files": validated_files,
            "total_requested": len(staging_files),
            "successfully_validated": len(validated_files)
        }
        
        if errors:
            logger.warning(f"Validation failed for {len(errors)} files: {errors}")
        else:
            logger.info(f"Successfully validated all {len(validated_files)} staging files")
        
        return result 