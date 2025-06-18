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
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json
from PIL import Image
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
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
        thumbnail_s3_keys = {}
        
        try:
            # Upload original image to storage
            uploaded_key = await self.storage.upload_file(file_data, s3_key, content_type)
            
            # Generate thumbnails
            thumbnails = self.generate_thumbnails(file_data, file_id, filename)
            
            # Upload each thumbnail
            for size_key, thumb_data in thumbnails.items():
                width, height = size_key.split('x')
                thumb_s3_key = self.generate_thumbnail_key(file_id, filename, int(width), int(height))
                
                try:
                    await self.storage.upload_file(thumb_data, thumb_s3_key, "image/jpeg")
                    thumbnail_s3_keys[size_key] = thumb_s3_key
                    logger.info(f"Uploaded thumbnail {size_key} for {file_id}")
                except Exception as e:
                    logger.error(f"Failed to upload thumbnail {size_key} for {file_id}: {e}")
            
            # Create database record for ownership tracking (SECURITY CRITICAL)
            image_record = UploadedImage(
                file_id=file_id,
                filename=filename,
                s3_key=s3_key,
                thumbnail_s3_keys=json.dumps(thumbnail_s3_keys) if thumbnail_s3_keys else None,
                user_id=user_id,
                content_type=content_type,
                file_size=len(file_data)
            )
            
            db.add(image_record)
            await db.commit()
            await db.refresh(image_record)
            
            logger.info(f"Image uploaded and ownership recorded: {file_id} -> {user_id}")
            
            # Return metadata with API URLs for access
            return {
                "file_id": file_id,
                "filename": filename,
                "content_type": content_type,
                "size": len(file_data),
                "s3_key": s3_key,
                "thumbnail_s3_keys": thumbnail_s3_keys,
                "url": f"{self.image_base_url}/{file_id}",  # Full-size image endpoint
                "uploaded_at": image_record.uploaded_at.isoformat(),
                "db_id": image_record.id
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {e}")
            # Clean up storage if database operation failed
            try:
                await self.storage.delete_file(s3_key)
                # Clean up any uploaded thumbnails
                for thumb_s3_key in thumbnail_s3_keys.values():
                    await self.storage.delete_file(thumb_s3_key)
            except:
                pass
            raise
    
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

# Global storage service instance
storage_service = ImageStorageService() 