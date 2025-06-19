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
from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.storage.storage import storage_service

logger = logging.getLogger(__name__)

@dataclass
class StagingMetadata:
    """Metadata structure for staged files"""
    file_id: str
    original_filename: str
    content_type: str
    file_size: int
    user_id: str
    staged_at: datetime
    expires_at: datetime
    state: str = "staging"  # "staging" or "committed"
    purpose: str = "vision"  # For future OpenAI commit
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_id': self.file_id,
            'original_filename': self.original_filename,
            'content_type': self.content_type,
            'file_size': str(self.file_size),
            'user_id': self.user_id,
            'staged_at': self.staged_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'state': self.state,
            'purpose': self.purpose
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StagingMetadata':
        return cls(
            file_id=data['file_id'],
            original_filename=data['original_filename'],
            content_type=data['content_type'],
            file_size=int(data['file_size']),
            user_id=data['user_id'],
            staged_at=datetime.fromisoformat(data['staged_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            state=data.get('state', 'staging'),
            purpose=data.get('purpose', 'vision')
        )

class StagingStorageService:
    """
    Enhanced Staging Storage Service for Image Management
    
    Features:
    - Uses same S3 key pattern as storage.py (no key conflicts)
    - Stores staging state in S3 object metadata
    - Supports future commit operations without file movement
    - Background cleanup of expired staging files
    - User isolation and access control
    """
    
    def __init__(self):
        self.storage_backend = storage_service.storage
        self.max_staging_age_hours = 24
        self.max_file_size = settings.MAX_IMAGE_SIZE
    
    def _validate_staging_file(self, filename: str, file_size: int) -> None:
        """Validate staging file before upload"""
        try:
            # Use existing validation from storage_service
            storage_service.validate_image_file(filename, file_size)
        except ValueError as e:
            # Convert ValueError to ValidationException for consistent error handling
            raise ValidationException(str(e))
    
    async def _upload_with_metadata(self, file_data: bytes, s3_key: str, content_type: str, metadata: Dict[str, Any]) -> str:
        """Upload file to S3 with metadata tags"""
        try:
            # Use boto3 client directly to add metadata
            self.storage_backend.s3_client.put_object(
                Bucket=self.storage_backend.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata=metadata  # Store metadata as S3 object metadata
            )
            
            logger.info(f"Uploaded file with metadata: {s3_key}")
            return s3_key
                
        except Exception as e:
            logger.error(f"Failed to upload file {s3_key} with metadata: {e}")
            raise
    
    async def _get_object_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an S3 object"""
        try:
            response = self.storage_backend.s3_client.head_object(
                Bucket=self.storage_backend.bucket_name,
                Key=s3_key
            )
            return response.get('Metadata', {})
        except Exception as e:
            logger.debug(f"Failed to get metadata for {s3_key}: {e}")
            return None
    
    async def _list_staging_files(self, prefix: str = "images/") -> List[Dict[str, Any]]:
        """List S3 objects in staging state"""
        try:
            response = self.storage_backend.s3_client.list_objects_v2(
                Bucket=self.storage_backend.bucket_name,
                Prefix=prefix
            )
            return response.get('Contents', [])
        except Exception as e:
            logger.error(f"Failed to list staging files: {e}")
            return []

    async def bulk_upload_to_staging(
        self,
        files_data: List[Tuple[bytes, str, str]],  # [(file_data, filename, content_type), ...]
        user_id: str,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Bulk upload files to staging area using same S3 key pattern as storage.py
        
        Args:
            files_data: List of (file_data, filename, content_type) tuples
            user_id: User ID for isolation
            max_concurrent: Maximum concurrent uploads
            
        Returns:
            Dict with upload results and file_ids (same as final storage would use)
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
            raise ValidationException(error_msg)
        
        # Process with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def stage_single_file(file_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # Generate file ID using storage.py method
                    file_id = storage_service.generate_file_id()
                    # Generate S3 key using storage.py method (same final location)
                    s3_key = storage_service.generate_storage_key(file_id, filename)
                    
                    # Create staging metadata
                    now = datetime.utcnow()
                    metadata = StagingMetadata(
                        file_id=file_id,
                        original_filename=filename,
                        content_type=content_type,
                        file_size=len(file_data),
                        user_id=user_id,
                        staged_at=now,
                        expires_at=now + timedelta(hours=self.max_staging_age_hours),
                        state="staging",
                        purpose="vision"
                    )
                    
                    # Upload file with staging metadata to final S3 location
                    await self._upload_with_metadata(
                        file_data=file_data,
                        s3_key=s3_key,
                        content_type=content_type,
                        metadata=metadata.to_dict()
                    )
                    
                    logger.info(f"Successfully staged: {file_id} at {s3_key} for user {user_id}")
                    
                    return {
                        "success": True,
                        "file_id": file_id,  # Return file_id instead of staging_id
                        "s3_key": s3_key,
                        "filename": filename,
                        "size": len(file_data),
                        "content_type": content_type,
                        "staged_at": now.isoformat(),
                        "expires_at": metadata.expires_at.isoformat()
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
                    "file_id": result["file_id"],  # Use file_id instead of staging_id
                    "s3_key": result["s3_key"],
                    "filename": result["filename"],
                    "size": result["size"],
                    "content_type": result["content_type"],
                    "staged_at": result["staged_at"],
                    "expires_at": result["expires_at"]
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
            "staged_files": successful_uploads,  # Contains file_ids
            "failed_files": failed_uploads,
            "total_size_bytes": total_size_bytes
        }
    
    async def discard_staged_file(self, file_id: str, user_id: str) -> bool:
        """
        Discard a staged file using file_id and ownership validation
        
        Args:
            file_id: File ID to discard (as returned from staging upload)
            user_id: User ID for validation
            
        Returns:
            True if successfully discarded, False otherwise
        """
        try:
            # Get staging metadata first
            metadata = await self.get_staging_metadata(file_id, user_id)
            if not metadata:
                logger.warning(f"Staged file {file_id} not found or access denied for user {user_id}")
                raise FileNotFoundError(f"Staged file {file_id} not found or access denied")
            
            # Use the same S3 key pattern as storage.py
            s3_key = storage_service.generate_storage_key(file_id, metadata.original_filename)
            
            # Delete file from S3
            success = await self.storage_backend.delete_file(s3_key)
            if success:
                logger.info(f"Successfully discarded staged file: {file_id} (key: {s3_key})")
                return True
            else:
                logger.warning(f"Failed to delete staged file: {s3_key}")
                return False
                
        except FileNotFoundError:
            # Re-raise ownership/not found errors
            raise
        except Exception as e:
            logger.error(f"Error discarding staged file {file_id}: {e}")
            raise
    
    async def bulk_discard_staged_files(self, file_ids: List[str], user_id: str) -> Dict[str, Any]:
        """
        Bulk discard multiple staged files using file_ids
        
        Args:
            file_ids: List of file IDs to discard (as returned from staging upload)
            user_id: User ID for validation
            
        Returns:
            Dict with discard results
        """
        logger.info(f"Bulk discarding {len(file_ids)} staged files for user {user_id}")
        
        discarded_files = []
        failed_discards = []
        
        for file_id in file_ids:
            try:
                await self.discard_staged_file(file_id, user_id)
                # If we get here, discard was successful (no exception thrown)
                discarded_files.append(file_id)
                    
            except FileNotFoundError as e:
                failed_discards.append({
                    "file_id": file_id,
                    "error": str(e)
                })
            except Exception as e:
                failed_discards.append({
                    "file_id": file_id,
                    "error": str(e)
                })
        
        return {
            "total_requested": len(file_ids),
            "successfully_discarded": len(discarded_files),
            "failed_discards": len(failed_discards),
            "discarded_file_ids": discarded_files,
            "failed_file_ids": failed_discards
        }
    
    async def get_staging_metadata(self, file_id: str, user_id: str) -> Optional[StagingMetadata]:
        """
        Get metadata for a staged file (needed for future commit and current operations)
        
        Args:
            file_id: File ID to get metadata for
            user_id: User ID for ownership validation
            
        Returns:
            StagingMetadata object if found and owned by user, None otherwise
        """
        try:
            # We need to check common extensions since we don't know the exact extension
            extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            
            for ext in extensions:
                # Generate potential S3 key with this extension
                test_filename = f"test{ext}"
                s3_key = storage_service.generate_storage_key(file_id, test_filename)
                
                try:
                    metadata_dict = await self._get_object_metadata(s3_key)
                    if metadata_dict and metadata_dict.get('state') == 'staging':
                        # Verify ownership
                        if metadata_dict.get('user_id') != user_id:
                            logger.warning(f"Access denied: file {file_id} doesn't belong to user {user_id}")
                            return None
                        
                        # Convert back to StagingMetadata object
                        return StagingMetadata.from_dict(metadata_dict)
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get staging metadata for {file_id}: {e}")
            return None
    
    async def list_user_staged_files(self, user_id: str) -> List[StagingMetadata]:
        """
        List all staged files for a user (needed for future commit operations)
        
        Args:
            user_id: User ID to list files for
            
        Returns:
            List of StagingMetadata objects for user's staged files
        """
        try:
            staging_objects = await self._list_staging_files()
            user_files = []
            
            for obj in staging_objects:
                try:
                    metadata_dict = await self._get_object_metadata(obj['Key'])
                    if (metadata_dict and 
                        metadata_dict.get('user_id') == user_id and 
                        metadata_dict.get('state') == 'staging'):
                        
                        metadata = StagingMetadata.from_dict(metadata_dict)
                        user_files.append(metadata)
                except Exception as e:
                    logger.debug(f"Error processing staging object {obj['Key']}: {e}")
                    continue
            
            return user_files
            
        except Exception as e:
            logger.error(f"Failed to list staged files for user {user_id}: {e}")
            return []
    
    async def cleanup_expired_staging_files(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Background cleanup of expired staging files
        
        Args:
            dry_run: If True, only report what would be cleaned, don't delete
            
        Returns:
            Dict with cleanup results
        """
        logger.info(f"Starting staging cleanup (dry_run={dry_run})")
        
        try:
            # List all files in images directory
            staging_objects = await self._list_staging_files()
            
            expired_files = []
            active_files = []
            cleanup_errors = []
            
            for obj in staging_objects:
                try:
                    # Extract metadata from S3 object
                    metadata_dict = await self._get_object_metadata(obj['Key'])
                    
                    # Only process files in staging state
                    if metadata_dict and metadata_dict.get('state') == 'staging':
                        expires_at_str = metadata_dict.get('expires_at')
                        if expires_at_str:
                            expires_at = datetime.fromisoformat(expires_at_str)
                            
                            if datetime.utcnow() > expires_at:
                                expired_files.append({
                                    'file_id': metadata_dict.get('file_id'),
                                    's3_key': obj['Key'],
                                    'expired_since': str(datetime.utcnow() - expires_at),
                                    'user_id': metadata_dict.get('user_id'),
                                    'original_filename': metadata_dict.get('original_filename')
                                })
                                
                                # Delete if not dry run
                                if not dry_run:
                                    await self.storage_backend.delete_file(obj['Key'])
                                    logger.info(f"Cleaned up expired staging file: {obj['Key']}")
                            else:
                                active_files.append({
                                    'file_id': metadata_dict.get('file_id'),
                                    'expires_in': str(expires_at - datetime.utcnow())
                                })
                        
                except Exception as e:
                    cleanup_errors.append({
                        'key': obj['Key'],
                        'error': str(e)
                    })
            
            result = {
                'cleanup_completed': not dry_run,
                'expired_files_found': len(expired_files),
                'expired_files_cleaned': len(expired_files) if not dry_run else 0,
                'active_files': len(active_files),
                'cleanup_errors': len(cleanup_errors),
                'expired_files': expired_files,
                'cleanup_errors': cleanup_errors
            }
            
            logger.info(f"Staging cleanup completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Staging cleanup failed: {e}")
            raise
    
    # Placeholder for future commit method
    async def commit_staged_files(self, file_ids: List[str], user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        PLACEHOLDER: Commit staged files to permanent storage
        
        This will be implemented later and will:
        1. Get staging metadata for each file_id
        2. Verify files are in staging state
        3. Update S3 metadata state from 'staging' to 'committed'
        4. Create database records in uploaded_images table
        5. Files are already in final S3 location - no movement needed!
        
        Args:
            file_ids: List of file IDs to commit (same as used for staging)
            user_id: User ID for validation
            db: Database session for creating records
            
        Returns:
            Dict with commit results
        """
        raise NotImplementedError("Commit functionality will be implemented in future phase")

# Create singleton instance
staging_service = StagingStorageService() 