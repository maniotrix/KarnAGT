"""
Storage Service for Image and File Management
Based on IMAGE_UPLOAD_FEATURE_SPEC.md - supports MinIO (dev) and S3 (prod)
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
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "chatgpt-files")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")  # None for AWS S3
        self.region = os.getenv("S3_REGION", "us-east-1")
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
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
                ContentType=content_type,
                ACL='public-read'  # For public image access
            )
            
            # Return public URL
            if self.endpoint_url:
                # MinIO URL
                return f"{self.endpoint_url}/{self.bucket_name}/{key}"
            else:
                # AWS S3 URL
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
                
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
        storage_backend = os.getenv("STORAGE_BACKEND", "minio").lower()
        
        if storage_backend == "s3" or storage_backend == "minio":
            self.storage = S3StorageBackend()
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")
        
        # Configuration
        self.max_image_size = int(os.getenv("MAX_IMAGE_SIZE", 20 * 1024 * 1024))  # 20MB
        self.allowed_types = os.getenv("ALLOWED_IMAGE_TYPES", ".png,.jpg,.jpeg,.gif,.webp").split(",")
        self.image_base_url = os.getenv("IMAGE_BASE_URL", "http://localhost:8000/api/images")
    
    def generate_file_id(self) -> str:
        """Generate unique file ID"""
        return f"img_{uuid.uuid4().hex[:8]}"
    
    def generate_storage_key(self, file_id: str, filename: str) -> str:
        """Generate S3 key for file storage"""
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        file_extension = os.path.splitext(filename)[1].lower()
        return f"images/{date_prefix}/{file_id}{file_extension}"
    
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
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload image and return metadata
        
        Returns:
            Dict containing file_id, urls, s3_key, etc.
        """
        # Validate file
        self.validate_image_file(filename, len(file_data))
        
        # Generate file ID and storage key
        file_id = self.generate_file_id()
        s3_key = self.generate_storage_key(file_id, filename)
        
        try:
            # Upload to storage
            display_url = await self.storage.upload_file(file_data, s3_key, content_type)
            
            # Return metadata
            return {
                "file_id": file_id,
                "filename": filename,
                "content_type": content_type,
                "size": len(file_data),
                "s3_key": s3_key,
                "urls": {
                    "display": display_url,
                    "api": f"{self.image_base_url}/{file_id}"
                },
                "uploaded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {e}")
            raise
    
    async def delete_image(self, s3_key: str) -> bool:
        """Delete image from storage"""
        return await self.storage.delete_file(s3_key)
    
    async def get_presigned_url(self, s3_key: str, expire_seconds: int = 3600) -> str:
        """Get presigned URL for secure access"""
        return await self.storage.generate_presigned_url(s3_key, expire_seconds)

# Global storage service instance
storage_service = ImageStorageService() 