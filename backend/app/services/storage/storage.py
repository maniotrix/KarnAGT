"""
Storage Service for Image and File Management
Based on IMAGE_UPLOAD_FEATURE_SPEC.md - supports MinIO (dev) and S3 (prod)
Uses database-driven access control (industry best practice)
"""

import os
import uuid
import boto3
from abc import ABC, abstractmethod
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging
import json
import asyncio
import time
from PIL import Image
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, desc, asc, and_, or_
from app.core.database import get_db, AsyncSessionLocal
from app.models.database.uploaded_image import UploadedImage
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """Abstract storage backend for file operations"""
    
    @abstractmethod
    async def upload_file(self, file_data: bytes, key: str, content_type: str) -> str:
        """Upload file and return URL"""
        pass
    
    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    async def generate_presigned_url(self, key: str, expire_seconds: int = 3600) -> str:
        """Generate presigned URL for secure access"""
        pass

class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend (MinIO/AWS S3)"""
    
    def __init__(self):
        # Use global settings instead of direct os.getenv calls
        self.bucket_name = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.region = settings.S3_REGION
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name=self.region
        )
    
    async def upload_file(self, file_data: bytes, key: str, content_type: str) -> str:
        """Upload file to S3/MinIO"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type
                # No ACL = private by default, no direct access
            )
            
            # File uploaded successfully, return the key for later API access
            # No direct URLs since files are private
            return key
                
        except ClientError as e:
            logger.error(f"Failed to upload file {key}: {e}")
            raise
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from S3/MinIO"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted file: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file {key}: {e}")
            return False
    
    async def generate_presigned_url(self, key: str, expire_seconds: int = 3600) -> str:
        """Generate presigned URL for secure access"""
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expire_seconds
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise

class ImageStorageService:
    """Main service for image and file storage operations"""
    
    def __init__(self):
        # Initialize storage backend based on configuration
        storage_backend = settings.STORAGE_BACKEND.lower()
        
        if storage_backend == "s3" or storage_backend == "minio":
            self.storage = S3StorageBackend()
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")
        
        # Configuration from settings
        self.max_image_size = settings.MAX_IMAGE_SIZE
        self.allowed_types = settings.get_allowed_image_types()
        self.image_base_url = settings.IMAGE_BASE_URL
    
    def generate_file_id(self) -> str:
        """Generate unique file ID"""
        return f"img_{uuid.uuid4().hex[:8]}"
    
    def generate_storage_key(self, file_id: str, filename: str) -> str:
        """Generate S3 key for file storage"""
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        file_extension = os.path.splitext(filename)[1].lower()
        return f"images/{date_prefix}/{file_id}{file_extension}"

    def generate_thumbnail_key(self, file_id: str, filename: str, width: int, height: int) -> str:
        """Generate S3 key for thumbnail storage"""
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        # Use JPEG for thumbnails by default to save space
        return f"thumbnails/{date_prefix}/{file_id}_thumb_{width}x{height}.jpg"

    def generate_thumbnails(self, image_data: bytes, file_id: str, filename: str) -> Dict[str, bytes]:
        """
        Generate thumbnails in different sizes
        
        Returns:
            Dict mapping size strings to thumbnail bytes
        """
        thumbnails = {}
        
        try:
            # Open original image
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary (for JPEG output)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Generate thumbnails for each configured size
                for width, height in settings.get_thumbnail_sizes():
                    # Create a copy for resizing
                    thumbnail = img.copy()
                    
                    # Resize maintaining aspect ratio
                    thumbnail.thumbnail((width, height), Image.Resampling.LANCZOS)
                    
                    # Save to bytes
                    thumb_buffer = io.BytesIO()
                    thumbnail.save(
                        thumb_buffer, 
                        format=settings.THUMBNAIL_FORMAT,
                        quality=settings.THUMBNAIL_QUALITY,
                        optimize=True
                    )
                    thumb_buffer.seek(0)
                    
                    size_key = f"{width}x{height}"
                    thumbnails[size_key] = thumb_buffer.getvalue()
                    
                    logger.info(f"Generated {size_key} thumbnail for {file_id}")
            
            return thumbnails
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnails for {file_id}: {e}")
            return {}
    
    def validate_image_file(self, filename: str, file_size: int) -> None:
        """Validate image file before upload"""
        # Check file size
        if file_size > self.max_image_size:
            raise ValueError(f"File too large. Max size: {self.max_image_size} bytes")
        
        # Check file type
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in self.allowed_types:
            raise ValueError(f"Invalid file type. Allowed: {', '.join(self.allowed_types)}")
    
    async def upload_image(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Upload image and store ownership in database (industry best practice)
        
        Returns:
            Dict containing file_id, urls, s3_key, etc.
        """
        # Validate file
        self.validate_image_file(filename, len(file_data))
        
        # Generate file ID and storage key
        file_id = self.generate_file_id()
        s3_key = self.generate_storage_key(file_id, filename)
        
        # Track uploaded assets for cleanup on failure
        uploaded_assets = {
            "main_file": None,
            "thumbnails": {}
        }
        
        try:
            # Start database transaction
            # Upload original image to storage
            uploaded_key = await self.storage.upload_file(file_data, s3_key, content_type)
            uploaded_assets["main_file"] = s3_key
            
            # Generate thumbnails
            thumbnails = self.generate_thumbnails(file_data, file_id, filename)
            
            # Upload each thumbnail
            for size_key, thumb_data in thumbnails.items():
                width, height = size_key.split('x')
                thumb_s3_key = self.generate_thumbnail_key(file_id, filename, int(width), int(height))
                
                try:
                    await self.storage.upload_file(thumb_data, thumb_s3_key, "image/jpeg")
                    uploaded_assets["thumbnails"][size_key] = thumb_s3_key
                    logger.info(f"Uploaded thumbnail {size_key} for {file_id}")
                except Exception as e:
                    logger.error(f"Failed to upload thumbnail {size_key} for {file_id}: {e}")
                    # Continue with partial thumbnails - not critical for main operation
            
            # Create database record for ownership tracking (SECURITY CRITICAL)
            image_record = UploadedImage(
                file_id=file_id,
                filename=filename,
                s3_key=s3_key,
                thumbnail_s3_keys=json.dumps(uploaded_assets["thumbnails"]) if uploaded_assets["thumbnails"] else None,
                user_id=user_id,
                content_type=content_type,
                file_size=len(file_data)
            )
            
            db.add(image_record)
            await db.commit()  # Commit database transaction
            await db.refresh(image_record)
            
            logger.info(f"Image uploaded and ownership recorded: {file_id} -> {user_id}")
            
            # Return metadata with API URLs for access
            return {
                "file_id": file_id,
                "filename": filename,
                "content_type": content_type,
                "size": len(file_data),
                "s3_key": s3_key,
                "thumbnail_s3_keys": uploaded_assets["thumbnails"],
                "url": f"{self.image_base_url}/{file_id}",  # Full-size image endpoint
                "uploaded_at": image_record.uploaded_at.isoformat(),
                "db_id": image_record.id
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {e}")
            
            # SAGA PATTERN: Compensating transactions for cleanup
            await self._cleanup_failed_upload(uploaded_assets)
            
            # Ensure database rollback
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Database rollback failed: {rollback_error}")
            
            raise
    
    async def _cleanup_failed_upload(self, uploaded_assets: Dict[str, Any]):
        """
        Cleanup uploaded assets when database operation fails
        Implements compensation pattern for cross-system consistency
        """
        cleanup_errors = []
        
        try:
            # Clean up main file
            if uploaded_assets["main_file"]:
                try:
                    await self.storage.delete_file(uploaded_assets["main_file"])
                    logger.info(f"Cleaned up main file: {uploaded_assets['main_file']}")
                except Exception as e:
                    cleanup_errors.append(f"Failed to cleanup main file: {e}")
            
            # Clean up thumbnails
            for size_key, thumb_s3_key in uploaded_assets["thumbnails"].items():
                try:
                    await self.storage.delete_file(thumb_s3_key)
                    logger.info(f"Cleaned up thumbnail {size_key}: {thumb_s3_key}")
                except Exception as e:
                    cleanup_errors.append(f"Failed to cleanup thumbnail {size_key}: {e}")
            
            if cleanup_errors:
                logger.warning(f"Upload cleanup had errors: {cleanup_errors}")
            
        except Exception as e:
            logger.error(f"Critical error during upload cleanup: {e}")
            # This is a critical issue - may need manual intervention
            # In production, this should trigger alerts
    
    async def delete_image(self, s3_key: str) -> bool:
        """Delete image from storage"""
        return await self.storage.delete_file(s3_key)
    
    async def get_presigned_url(self, s3_key: str, expire_seconds: int = 3600) -> str:
        """Get presigned URL for secure access"""
        return await self.storage.generate_presigned_url(s3_key, expire_seconds)
    
    async def validate_file_ownership(self, file_id: str, user_id: str, db: AsyncSession) -> Optional[UploadedImage]:
        """
        Validate that user owns the file - SECURITY CRITICAL
        
        This is the industry standard approach for file access control.
        Returns the image record if user owns it, None otherwise.
        """
        try:
            query = select(UploadedImage).where(
                UploadedImage.file_id == file_id,
                UploadedImage.user_id == user_id
            )
            result = await db.execute(query)
            image_record = result.scalar_one_or_none()
            
            if image_record:
                logger.info(f"Access granted: {file_id} -> {user_id}")
                return image_record
            else:
                logger.warning(f"Access denied: {file_id} -> {user_id} (ownership check failed)")
                return None
                
        except Exception as e:
            logger.error(f"Error validating file ownership {file_id} for {user_id}: {e}")
            return None
    
    async def serve_image_securely(self, file_id: str, user_id: str, db: AsyncSession) -> Optional[str]:
        """
        Generate secure presigned URL only if user owns the file
        
        This implements proper access control validation using database ownership
        """
        # Validate ownership via database lookup (SECURITY CRITICAL)
        image_record = await self.validate_file_ownership(file_id, user_id, db)
        
        if not image_record:
            return None
            
        try:
            # Update last accessed timestamp
            update_query = update(UploadedImage).where(
                UploadedImage.id == image_record.id
            ).values(accessed_at=datetime.now())
            await db.execute(update_query)
            await db.commit()
            
            # Generate presigned URL for authorized access
            presigned_url = await self.get_presigned_url(image_record.s3_key, expire_seconds=3600)
            
            logger.info(f"Presigned URL generated for {file_id} by {user_id}")
            return presigned_url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {file_id}: {e}")
            return None
    
    async def serve_thumbnail_securely(self, file_id: str, size: str, user_id: str, db: AsyncSession) -> Optional[str]:
        """
        Generate secure presigned URL for thumbnail only if user owns the file
        
        Args:
            file_id: The image file ID
            size: Thumbnail size in format "WxH" (e.g., "150x150")
            user_id: User requesting access
            db: Database session
        
        Returns:
            Presigned URL for thumbnail or None if access denied
        """
        # Validate ownership via database lookup (SECURITY CRITICAL)
        image_record = await self.validate_file_ownership(file_id, user_id, db)
        
        if not image_record:
            return None
        
        # Check if thumbnail exists
        if image_record.thumbnail_s3_keys is None or image_record.thumbnail_s3_keys.strip() == "":
            logger.warning(f"No thumbnails found for {file_id}")
            return None
        
        try:
            # Parse thumbnail S3 keys
            thumbnail_keys = json.loads(image_record.thumbnail_s3_keys)
            
            if size not in thumbnail_keys:
                logger.warning(f"Thumbnail size {size} not found for {file_id}")
                return None
            
            # Update last accessed timestamp
            update_query = update(UploadedImage).where(
                UploadedImage.id == image_record.id
            ).values(accessed_at=datetime.now())
            await db.execute(update_query)
            await db.commit()
            
            # Generate presigned URL for thumbnail
            thumbnail_s3_key = thumbnail_keys[size]
            presigned_url = await self.get_presigned_url(thumbnail_s3_key, expire_seconds=3600)
            
            logger.info(f"Thumbnail presigned URL generated for {file_id} ({size}) by {user_id}")
            return presigned_url
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail presigned URL for {file_id}: {e}")
            return None
    
    async def get_user_images(self, user_id: str, db: AsyncSession, limit: int = 100, offset: int = 0) -> list[UploadedImage]:
        """Get list of images owned by user"""
        query = select(UploadedImage).where(
            UploadedImage.user_id == user_id
        ).order_by(UploadedImage.uploaded_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def delete_image_securely(self, file_id: str, user_id: str, db: AsyncSession) -> bool:
        """
        Delete image with ownership validation - SECURITY CRITICAL
        
        This follows the secure deletion pattern:
        1. Validate ownership via database lookup
        2. Delete from S3/MinIO storage
        3. Remove database record
        4. Return success/failure status
        """
        try:
            # SECURITY: Validate ownership first
            image_record = await self.validate_file_ownership(file_id, user_id, db)
            
            if not image_record:
                logger.warning(f"Delete denied: {file_id} -> {user_id} (ownership check failed)")
                return False
            
            # Delete from S3/MinIO storage
            try:
                await self.storage.delete_file(image_record.s3_key)
                logger.info(f"Deleted S3 file: {image_record.s3_key}")
                
                # Delete thumbnails if they exist
                if image_record.thumbnail_s3_keys is not None and image_record.thumbnail_s3_keys.strip() != "":
                    try:
                        thumbnail_keys = json.loads(image_record.thumbnail_s3_keys)
                        for size, thumb_s3_key in thumbnail_keys.items():
                            try:
                                await self.storage.delete_file(thumb_s3_key)
                                logger.info(f"Deleted thumbnail {size}: {thumb_s3_key}")
                            except Exception as e:
                                logger.error(f"Failed to delete thumbnail {size} for {image_record.file_id}: {e}")
                    except Exception as e:
                        logger.error(f"Failed to parse thumbnail keys during deletion for {image_record.file_id}: {e}")
            
            except Exception as e:
                logger.error(f"Failed to delete S3 file {image_record.s3_key}: {e}")
                # Continue with database deletion even if S3 deletion fails
                # This prevents orphaned database records
            
            # Delete from database
            await db.delete(image_record)
            await db.commit()
            
            logger.info(f"Successfully deleted image {file_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting image {file_id} for {user_id}: {e}")
            await db.rollback()
            return False

    # Bulk Operations
    async def bulk_upload_images(
        self,
        files_data: List[Tuple[bytes, str, str]],  # [(file_data, filename, content_type), ...]
        user_id: str,
        db: AsyncSession,
        conversation_id: Optional[str] = None,
        max_concurrent: int = 5,
        generate_thumbnails: bool = True
    ) -> Dict[str, Any]:
        """
        Bulk upload multiple images with concurrency control
        
        Args:
            files_data: List of tuples (file_data, filename, content_type)
            user_id: User performing the upload
            db: Database session
            conversation_id: Optional conversation context
            max_concurrent: Maximum concurrent uploads
            generate_thumbnails: Whether to generate thumbnails
            
        Returns:
            Dict with upload results and statistics
        """
        start_time = time.time()
        total_requested = len(files_data)
        uploaded_images = []
        failed_images = []
        total_size_bytes = 0
        
        # Calculate total size for quota estimation
        for file_data, _, _ in files_data:
            total_size_bytes += len(file_data)
        
        logger.info(f"Starting bulk upload of {total_requested} images for user {user_id}, total size: {total_size_bytes} bytes")
        
        # Process files in batches with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def upload_single_image(file_data: bytes, filename: str, content_type: str) -> Tuple[bool, Any]:
            async with semaphore:
                original_method = None
                # Create a separate database session for each concurrent upload to avoid conflicts
                async with AsyncSessionLocal() as upload_db:
                    try:
                        # Create a temporary modified method that respects generate_thumbnails flag
                        if not generate_thumbnails:
                            # Store original method temporarily
                            original_method = self.generate_thumbnails
                            # Replace with empty method
                            self.generate_thumbnails = lambda *args, **kwargs: {}
                        
                        result = await self.upload_image(
                            file_data=file_data,
                            filename=filename,
                            content_type=content_type,
                            user_id=user_id,
                            db=upload_db  # Use separate session
                        )
                        
                        # Restore original method if it was modified
                        if not generate_thumbnails and original_method:
                            self.generate_thumbnails = original_method
                        
                        return True, result
                    except Exception as e:
                        if not generate_thumbnails and original_method:
                            self.generate_thumbnails = original_method
                        return False, {"filename": filename, "error": str(e)}
        
        # Execute uploads concurrently
        tasks = [
            upload_single_image(file_data, filename, content_type)
            for file_data, filename, content_type in files_data
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_images.append({
                    "filename": files_data[i][1],
                    "error": str(result)
                })
            else:
                if isinstance(result, tuple) and len(result) == 2:
                    success, data = result
                    if success:
                        uploaded_images.append(data)
                    else:
                        failed_images.append(data)
                else:
                    failed_images.append({
                        "filename": files_data[i][1],
                        "error": "Invalid result format"
                    })
        
        upload_duration = time.time() - start_time
        
        # Estimate quota consumed (rough calculation)
        quota_consumed = len(uploaded_images) * 0.005  # $0.005 per successful upload
        
        logger.info(f"Bulk upload completed: {len(uploaded_images)} successful, {len(failed_images)} failed, {upload_duration:.2f}s")
        
        return {
            "total_requested": total_requested,
            "successfully_uploaded": len(uploaded_images),
            "failed_uploads": len(failed_images),
            "uploaded_images": uploaded_images,
            "failed_images": failed_images,
            "total_size_bytes": total_size_bytes,
            "upload_duration_seconds": upload_duration,
            "quota_consumed_usd": quota_consumed
        }
    
    async def bulk_delete_images(
        self,
        file_ids: List[str],
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Bulk delete multiple images with ownership validation
        
        Args:
            file_ids: List of file IDs to delete
            user_id: User performing the deletion
            db: Database session
            
        Returns:
            Dict with deletion results and statistics
        """
        logger.info(f"Starting bulk deletion of {len(file_ids)} images for user {user_id}")
        
        total_requested = len(file_ids)
        deleted_file_ids = []
        failed_file_ids = []
        freed_storage_bytes = 0
        
        for file_id in file_ids:
            try:
                # Get image record for size calculation before deletion
                image_record = await self.validate_file_ownership(file_id, user_id, db)
                if image_record:
                    file_size = image_record.file_size
                else:
                    file_size = 0
                
                # Attempt deletion
                success = await self.delete_image_securely(file_id, user_id, db)
                
                if success:
                    deleted_file_ids.append(file_id)
                    freed_storage_bytes += file_size
                else:
                    failed_file_ids.append({
                        "file_id": file_id,
                        "error": "Deletion failed or access denied"
                    })
                    
            except Exception as e:
                failed_file_ids.append({
                    "file_id": file_id,
                    "error": str(e)
                })
        
        logger.info(f"Bulk deletion completed: {len(deleted_file_ids)} successful, {len(failed_file_ids)} failed")
        
        return {
            "total_requested": total_requested,
            "successfully_deleted": len(deleted_file_ids),
            "failed_deletions": len(failed_file_ids),
            "deleted_file_ids": deleted_file_ids,
            "failed_file_ids": failed_file_ids,
            "freed_storage_bytes": freed_storage_bytes
        }
    
    async def bulk_get_metadata(
        self,
        file_ids: List[str],
        user_id: str,
        db: AsyncSession,
        include_urls: bool = True,
        include_thumbnails: bool = True
    ) -> Dict[str, Any]:
        """
        Bulk retrieve metadata for multiple images
        
        Args:
            file_ids: List of file IDs
            user_id: User requesting metadata
            db: Database session
            include_urls: Include access URLs
            include_thumbnails: Include thumbnail URLs
            
        Returns:
            Dict with metadata results
        """
        logger.info(f"Bulk metadata retrieval for {len(file_ids)} images for user {user_id}")
        
        total_requested = len(file_ids)
        images_metadata = []
        missing_file_ids = []
        
        # Query all images at once for efficiency
        query = select(UploadedImage).where(
            and_(
                UploadedImage.file_id.in_(file_ids),
                UploadedImage.user_id == user_id
            )
        )
        result = await db.execute(query)
        found_images = list(result.scalars().all())
        
        # Create lookup dict for found images
        found_dict = {img.file_id: img for img in found_images}
        
        # Process all requested file IDs
        for file_id in file_ids:
            if file_id in found_dict:
                img = found_dict[file_id]
                
                # Build URLs if requested
                urls = {}
                if include_urls:
                    urls["api"] = f"{self.image_base_url}/{img.file_id}"
                    
                    if include_thumbnails and img.thumbnail_s3_keys is not None:
                        try:
                            thumbnail_keys = json.loads(img.thumbnail_s3_keys)
                            for size in thumbnail_keys.keys():
                                urls[f"thumbnail_{size}"] = f"{self.image_base_url}/{img.file_id}/thumbnail?size={size}"
                        except Exception as e:
                            logger.warning(f"Failed to parse thumbnail keys for {img.file_id}: {e}")
                
                images_metadata.append({
                    "file_id": img.file_id,
                    "filename": img.filename,
                    "original_filename": img.filename,
                    "content_type": img.content_type,
                    "size": img.file_size,
                    "dimensions": None,  # Could extract from tags if stored
                    "s3_key": img.s3_key,
                    "urls": urls,
                    "uploaded_at": img.uploaded_at,
                    "is_deleted": False
                })
            else:
                missing_file_ids.append(file_id)
        
        return {
            "total_requested": total_requested,
            "found_images": len(images_metadata),
            "missing_images": len(missing_file_ids),
            "images_metadata": images_metadata,
            "missing_file_ids": missing_file_ids
        }
    
    async def search_images(
        self,
        user_id: str,
        db: AsyncSession,
        query: Optional[str] = None,
        content_type: Optional[str] = None,
        size_min: Optional[int] = None,
        size_max: Optional[int] = None,
        uploaded_after: Optional[datetime] = None,
        uploaded_before: Optional[datetime] = None,
        has_thumbnails: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "uploaded_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Search user's images with advanced filtering
        
        Args:
            user_id: User performing the search
            db: Database session
            query: Text search in filename
            content_type: Filter by content type
            size_min/size_max: File size range filters
            uploaded_after/uploaded_before: Date range filters
            has_thumbnails: Filter by thumbnail presence
            tags: Filter by tags (if implemented)
            limit: Number of results per page
            offset: Results to skip
            sort_by: Field to sort by
            sort_order: Sort direction
            
        Returns:
            Dict with search results and metadata
        """
        start_time = time.time()
        
        # Build query conditions
        conditions = [UploadedImage.user_id == user_id]
        
        if query:
            conditions.append(UploadedImage.filename.ilike(f"%{query}%"))
        
        if content_type:
            conditions.append(UploadedImage.content_type == content_type)
        
        if size_min is not None:
            conditions.append(UploadedImage.file_size >= size_min)
        
        if size_max is not None:
            conditions.append(UploadedImage.file_size <= size_max)
        
        if uploaded_after:
            conditions.append(UploadedImage.uploaded_at >= uploaded_after)
        
        if uploaded_before:
            conditions.append(UploadedImage.uploaded_at <= uploaded_before)
        
        if has_thumbnails is not None:
            if has_thumbnails:
                conditions.append(UploadedImage.thumbnail_s3_keys.isnot(None))
                conditions.append(UploadedImage.thumbnail_s3_keys != "")
            else:
                conditions.append(or_(
                    UploadedImage.thumbnail_s3_keys.is_(None),
                    UploadedImage.thumbnail_s3_keys == ""
                ))
        
        if tags:
            # Assuming tags are stored as JSON string
            for tag in tags:
                conditions.append(UploadedImage.tags.ilike(f"%{tag}%"))
        
        # Build base query
        base_query = select(UploadedImage).where(and_(*conditions))
        
        # Add sorting
        sort_column = getattr(UploadedImage, sort_by)
        if sort_order == "desc":
            base_query = base_query.order_by(desc(sort_column))
        else:
            base_query = base_query.order_by(asc(sort_column))
        
        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total_found = count_result.scalar()
        
        # Get paginated results
        search_query = base_query.limit(limit).offset(offset)
        result = await db.execute(search_query)
        images = list(result.scalars().all())
        
        # Convert to response format
        images_metadata = []
        for img in images:
            urls = {"api": f"{self.image_base_url}/{img.file_id}"}
            
            if img.thumbnail_s3_keys is not None:
                try:
                    thumbnail_keys = json.loads(img.thumbnail_s3_keys)
                    for size in thumbnail_keys.keys():
                        urls[f"thumbnail_{size}"] = f"{self.image_base_url}/{img.file_id}/thumbnail?size={size}"
                except Exception:
                    pass
            
            images_metadata.append({
                "file_id": img.file_id,
                "filename": img.filename,
                "original_filename": img.filename,
                "content_type": img.content_type,
                "size": img.file_size,
                "dimensions": None,
                "s3_key": img.s3_key,
                "urls": urls,
                "uploaded_at": img.uploaded_at,
                "is_deleted": False
            })
        
        search_duration = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        
        return {
            "query_summary": {
                "text_query": query,
                "content_type": content_type,
                "size_range": [size_min, size_max],
                "date_range": [uploaded_after, uploaded_before],
                "has_thumbnails": has_thumbnails,
                "tags": tags,
                "sort_by": sort_by,
                "sort_order": sort_order
            },
            "images": images_metadata,
            "total_found": total_found,
            "page": (offset // limit) + 1,
            "size": limit,
            "has_next": (offset + limit) < (total_found or 0),
            "has_prev": offset > 0,
            "search_duration_ms": search_duration
        }
    
    async def get_user_image_statistics(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics about user's images
        
        Args:
            user_id: User to get statistics for
            db: Database session
            
        Returns:
            Dict with various image statistics
        """
        logger.info(f"Generating image statistics for user {user_id}")
        
        # Base query for user's images
        base_query = select(UploadedImage).where(UploadedImage.user_id == user_id)
        
        # Total count and storage
        count_query = select(
            func.count(UploadedImage.id).label('total_images'),
            func.sum(UploadedImage.file_size).label('total_storage_bytes'),
            func.avg(UploadedImage.file_size).label('average_file_size'),
            func.max(UploadedImage.file_size).label('largest_file_size'),
            func.min(UploadedImage.file_size).label('smallest_file_size')
        ).where(UploadedImage.user_id == user_id)
        
        result = await db.execute(count_query)
        stats = result.first()
        
        # Images by content type
        type_query = select(
            UploadedImage.content_type,
            func.count(UploadedImage.id).label('count')
        ).where(UploadedImage.user_id == user_id).group_by(UploadedImage.content_type)
        
        type_result = await db.execute(type_query)
        images_by_type = {row.content_type: row.count for row in type_result}
        
        # Images by month
        month_expr = func.date_trunc('month', UploadedImage.uploaded_at)
        month_query = select(
            month_expr.label('month'),
            func.count(UploadedImage.id).label('count')
        ).where(UploadedImage.user_id == user_id).group_by(
            month_expr
        ).order_by(month_expr)
        
        month_result = await db.execute(month_query)
        images_by_month = {
            row.month.strftime('%Y-%m'): row.count 
            for row in month_result
            if row.month is not None
        }
        
        # Thumbnail count
        thumbnail_query = select(func.count(UploadedImage.id)).where(
            and_(
                UploadedImage.user_id == user_id,
                UploadedImage.thumbnail_s3_keys.isnot(None),
                UploadedImage.thumbnail_s3_keys != ""
            )
        )
        
        thumbnail_result = await db.execute(thumbnail_query)
        total_thumbnails = thumbnail_result.scalar()
        
        # Calculate quota usage (assuming $10 default quota)
        default_quota = 10.0  # Could get from user record or settings
        estimated_usage = (stats.total_images or 0) * 0.005  # $0.005 per image
        quota_used_percentage = min(100.0, (estimated_usage / default_quota) * 100)
        
        return {
            "total_images": stats.total_images or 0,
            "total_storage_bytes": stats.total_storage_bytes or 0,
            "total_thumbnails": total_thumbnails or 0,
            "images_by_type": images_by_type,
            "images_by_month": images_by_month,
            "average_file_size": int(stats.average_file_size or 0),
            "largest_file_size": stats.largest_file_size or 0,
            "smallest_file_size": stats.smallest_file_size or 0,
            "quota_used_percentage": quota_used_percentage,
            "storage_used_mb": round((stats.total_storage_bytes or 0) / (1024 * 1024), 2)
        }

# Global storage service instance
storage_service = ImageStorageService() 