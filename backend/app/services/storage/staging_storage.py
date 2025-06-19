"""
Staging Storage Service for Image Management
Handles staging area operations for optimized LLM inference workflow
"""

import os
import uuid
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.storage.storage import storage_service

logger = logging.getLogger(__name__)

class StagingStorageService:
    """
    Simplified Staging Storage Service for Image Management
    
    Features:
    - Simple staging uploads with staging_id as the S3 key
    - Direct discard operations using staging_id
    - No complex metadata files or nested directories
    - User isolation through staging_id prefixing
    """
    
    def __init__(self):
        self.storage_backend = storage_service.storage
        self.staging_prefix = "staging"
        self.max_staging_age_hours = 24
        self.max_file_size = settings.MAX_IMAGE_SIZE
    
    def _generate_staging_id(self, user_id: str) -> str:
        """Generate unique staging ID with user prefix for isolation"""
        return f"{self.staging_prefix}_{user_id}_{uuid.uuid4().hex[:12]}"
    
    def _build_staging_key(self, staging_id: str, filename: str) -> str:
        """Build S3 key for staging file - staging_id IS the key"""
        file_extension = os.path.splitext(filename)[1].lower()
        return f"{staging_id}{file_extension}"
    
    def _validate_staging_file(self, filename: str, file_size: int) -> None:
        """Validate staging file before upload"""
        try:
            # Use existing validation from storage_service
            storage_service.validate_image_file(filename, file_size)
        except ValueError as e:
            # Convert ValueError to ValidationException for consistent error handling
            raise ValidationException(str(e))
    
    def _extract_user_id_from_staging_id(self, staging_id: str) -> Optional[str]:
        """Extract user ID from staging ID for ownership validation"""
        try:
            parts = staging_id.split('_')
            if len(parts) >= 3 and parts[0] == self.staging_prefix:
                return parts[1]
            return None
        except:
            return None

    async def bulk_upload_to_staging(
        self,
        files_data: List[Tuple[bytes, str, str]],  # [(file_data, filename, content_type), ...]
        user_id: str,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Bulk upload files to staging area with concurrent processing
        
        Args:
            files_data: List of (file_data, filename, content_type) tuples
            user_id: User ID for isolation
            max_concurrent: Maximum concurrent uploads
            
        Returns:
            Dict with upload results and staging IDs
        """
        if not files_data:
            return {
                "total_requested": 0,
                "successfully_staged": 0,
                "failed_uploads": 0,
                "staged_files": [],
                "failed_files": [],
                "total_size_bytes": 0
            }
        
        logger.info(f"Bulk staging upload: {len(files_data)} files for user {user_id}")
        
        # First, validate ALL files before uploading any (fail fast for validation errors)
        validation_errors = []
        for file_data, filename, content_type in files_data:
            try:
                self._validate_staging_file(filename, len(file_data))
            except ValueError as e:
                validation_errors.append(f"File '{filename}': {str(e)}")
        
        # If any validation errors, raise ValidationException immediately
        if validation_errors:
            error_msg = "Validation failed for files: " + "; ".join(validation_errors)
            logger.warning(f"Bulk staging validation failed: {error_msg}")
            from app.core.exceptions import ValidationException
            raise ValidationException(error_msg)
        
        # Process with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def stage_single_file(file_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # File is already validated above, so we don't need to validate again
                    
                    # Generate staging ID (this IS the file ID client gets back)
                    staging_id = self._generate_staging_id(user_id)
                    staging_key = self._build_staging_key(staging_id, filename)
                    
                    # Upload file to staging - simple direct upload
                    await self.storage_backend.upload_file(
                        file_data=file_data,
                        key=staging_key,
                        content_type=content_type
                    )
                    
                    logger.info(f"Successfully staged: {staging_id} for user {user_id}")
                    
                    return {
                        "success": True,
                        "staging_id": staging_id,
                        "filename": filename,
                        "size": len(file_data),
                        "content_type": content_type
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to stage file {filename}: {e}")
                    return {
                        "success": False,
                        "filename": filename,
                        "error": str(e)
                    }
        
        # Execute concurrent uploads
        tasks = [
            stage_single_file(file_data, filename, content_type)
            for file_data, filename, content_type in files_data
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_uploads = []
        failed_uploads = []
        total_size_bytes = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_uploads.append({
                    "filename": "unknown",
                    "error": str(result)
                })
            elif isinstance(result, dict) and result.get("success"):
                successful_uploads.append({
                    "staging_id": result["staging_id"],
                    "filename": result["filename"],
                    "size": result["size"],
                    "content_type": result["content_type"]
                })
                total_size_bytes += result["size"]
            elif isinstance(result, dict):
                failed_uploads.append({
                    "filename": result.get("filename", "unknown"),
                    "error": result.get("error", "Unknown error")
                })
        
        return {
            "total_requested": len(files_data),
            "successfully_staged": len(successful_uploads),
            "failed_uploads": len(failed_uploads),
            "staged_files": successful_uploads,
            "failed_files": failed_uploads,
            "total_size_bytes": total_size_bytes
        }
    
    async def discard_staged_file(self, staging_id: str, user_id: str) -> bool:
        """
        Discard a single staged file - SIMPLE VERSION
        
        Args:
            staging_id: Staging ID to discard (client sends back what they got)
            user_id: User ID for validation
            
        Returns:
            True if successfully discarded, False otherwise
        """
        try:
            # SECURITY: Verify ownership by checking staging_id contains user_id
            staging_user_id = self._extract_user_id_from_staging_id(staging_id)
            if staging_user_id != user_id:
                logger.warning(f"Access denied: staging {staging_id} doesn't belong to user {user_id}")
                raise FileNotFoundError(f"Staging file {staging_id} not found or access denied")
            
            # Find the actual S3 key - try common extensions
            extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            
            files_found = []
            for ext in extensions:
                staging_key = f"{staging_id}{ext}"
                try:
                    # Check if file exists before deleting
                    # S3 delete operations are idempotent - they succeed whether file exists or not
                    # So we need to check existence first
                    self.storage_backend.s3_client.head_object(
                        Bucket=self.storage_backend.bucket_name,
                        Key=staging_key
                    )
                    # If we get here, the file exists
                    files_found.append(staging_key)
                    logger.debug(f"Found staging file: {staging_key}")
                except Exception as e:
                    # File doesn't exist or other error
                    logger.debug(f"Staging key {staging_key} does not exist: {e}")
                    continue
            
            # If no files found with any extension, raise FileNotFoundError
            if not files_found:
                logger.warning(f"Staged file {staging_id} not found with any extension")
                raise FileNotFoundError(f"Staging file {staging_id} not found")
            
            # Delete all found files
            for staging_key in files_found:
                try:
                    success = await self.storage_backend.delete_file(staging_key)
                    if success:
                        logger.info(f"Successfully discarded staged file: {staging_id} (key: {staging_key})")
                    else:
                        logger.warning(f"Failed to delete staging file: {staging_key}")
                except Exception as e:
                    logger.error(f"Error deleting staging file {staging_key}: {e}")
                    
            return True
                
        except FileNotFoundError:
            # Re-raise ownership/not found errors
            raise
        except Exception as e:
            logger.error(f"Error discarding staged file {staging_id}: {e}")
            raise
    
    async def bulk_discard_staged_files(self, staging_ids: List[str], user_id: str) -> Dict[str, Any]:
        """
        Bulk discard multiple staged files - SIMPLE VERSION
        
        Args:
            staging_ids: List of staging IDs to discard (what client got back from upload)
            user_id: User ID for validation
            
        Returns:
            Dict with discard results
        """
        logger.info(f"Bulk discarding {len(staging_ids)} staged files for user {user_id}")
        
        discarded_files = []
        failed_discards = []
        
        for staging_id in staging_ids:
            try:
                await self.discard_staged_file(staging_id, user_id)
                # If we get here, discard was successful (no exception thrown)
                discarded_files.append(staging_id)
                    
            except FileNotFoundError as e:
                failed_discards.append({
                    "staging_id": staging_id,
                    "error": str(e)
                })
            except Exception as e:
                failed_discards.append({
                    "staging_id": staging_id,
                    "error": str(e)
                })
        
        return {
            "total_requested": len(staging_ids),
            "successfully_discarded": len(discarded_files),
            "failed_discards": len(failed_discards),
            "discarded_staging_ids": discarded_files,
            "failed_staging_ids": failed_discards
        }

# Create singleton instance
staging_service = StagingStorageService() 