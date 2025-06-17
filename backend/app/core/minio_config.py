"""
MinIO Configuration for Image and File Storage
Handles MinIO client setup for image upload functionality
"""

import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MinIOConfig:
    """MinIO configuration for image and file storage"""
    
    def __init__(self):
        # Get configuration from environment variables
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
        self.access_key = os.getenv("S3_ACCESS_KEY_ID", "minioadmin")
        self.secret_key = os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin123")
        self.region = os.getenv("S3_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "chatgpt-files")
        
        self._client = None
    
    @property
    def client(self):
        """Get or create MinIO client"""
        if self._client is None:
            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version='s3v4'),
                region_name=self.region
            )
        return self._client
    
    def get_bucket_name(self) -> str:
        """Get the main bucket name for file storage"""
        return self.bucket_name
    
    async def ensure_bucket_exists(self, bucket_name: str) -> bool:
        """Ensure a bucket exists, create if it doesn't"""
        try:
            self.client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' exists")
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                # Bucket doesn't exist, create it
                try:
                    self.client.create_bucket(Bucket=bucket_name)
                    logger.info(f"Created bucket '{bucket_name}'")
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket '{bucket_name}': {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket '{bucket_name}': {e}")
                return False
    
    def generate_presigned_url(
        self, 
        bucket_name: str, 
        object_key: str, 
        expiration: int = 3600,
        method: str = 'GET'
    ) -> Optional[str]:
        """Generate a presigned URL for object access"""
        try:
            response = self.client.generate_presigned_url(
                method.lower() + '_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    def upload_file(self, file_path: str, bucket_name: str, object_key: str) -> bool:
        """Upload a file to MinIO"""
        try:
            self.client.upload_file(file_path, bucket_name, object_key)
            logger.info(f"Uploaded '{file_path}' to bucket '{bucket_name}' as '{object_key}'")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    
    def download_file(self, bucket_name: str, object_key: str, file_path: str) -> bool:
        """Download a file from MinIO"""
        try:
            self.client.download_file(bucket_name, object_key, file_path)
            logger.info(f"Downloaded '{object_key}' from bucket '{bucket_name}' to '{file_path}'")
            return True
        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    def delete_file(self, bucket_name: str, object_key: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.delete_object(Bucket=bucket_name, Key=object_key)
            logger.info(f"Deleted '{object_key}' from bucket '{bucket_name}'")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False

# Global MinIO configuration instance
minio_config = MinIOConfig() 