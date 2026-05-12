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

import re
from typing import List, Tuple


def validate_bucket_name(bucket_name: str) -> Tuple[bool, List[str]]:
    """
    Validate bucket name according to S3/MinIO naming conventions
    
    AWS S3 Bucket naming rules:
    - Must be between 3 and 63 characters long
    - Can contain only lowercase letters, numbers, and hyphens
    - Cannot contain uppercase characters or underscores
    - Cannot start or end with a hyphen
    - Cannot have consecutive hyphens
    - Must not be formatted as an IP address (e.g., 192.168.1.1)
    
    Args:
        bucket_name: The bucket name to validate
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        - is_valid: True if the bucket name is valid
        - errors: List of specific validation errors (empty if valid)
    """
    errors = []
    
    # Check if bucket_name is provided
    if not bucket_name:
        errors.append("Bucket name cannot be empty")
        return False, errors
    
    # Check length (3-63 characters)
    if len(bucket_name) < 3:
        errors.append("Bucket name must be at least 3 characters long")
    elif len(bucket_name) > 63:
        errors.append("Bucket name cannot exceed 63 characters")
    
    # Check for valid characters (lowercase letters, numbers, hyphens only)
    if not re.match(r'^[a-z0-9-]+$', bucket_name):
        invalid_chars = set(char for char in bucket_name if not re.match(r'[a-z0-9-]', char))
        if invalid_chars:
            errors.append(f"Bucket name contains invalid characters: {', '.join(sorted(invalid_chars))}. Only lowercase letters, numbers, and hyphens are allowed")
    
    # Check for uppercase letters specifically (common mistake)
    if any(char.isupper() for char in bucket_name):
        errors.append("Bucket name cannot contain uppercase letters")
    
    # Check for underscores specifically (common mistake)
    if '_' in bucket_name:
        errors.append("Bucket name cannot contain underscores. Use hyphens (-) instead")
    
    # Check start/end with hyphen
    if bucket_name.startswith('-'):
        errors.append("Bucket name cannot start with a hyphen")
    if bucket_name.endswith('-'):
        errors.append("Bucket name cannot end with a hyphen")
    
    # Check for consecutive hyphens
    if '--' in bucket_name:
        errors.append("Bucket name cannot contain consecutive hyphens")
    
    # Check if it looks like an IP address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, bucket_name):
        errors.append("Bucket name cannot be formatted as an IP address")
    
    # Check for dots (not recommended for SSL/TLS)
    if '.' in bucket_name:
        errors.append("Bucket name should not contain dots (.) as they can cause SSL/TLS certificate issues")
    
    is_valid = len(errors) == 0
    return is_valid, errors

logger = logging.getLogger(__name__)

class MinIOConfig:
    """MinIO configuration for image and file storage"""
    
    def __init__(self):
        # Get configuration from environment variables
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
        self.access_key = os.getenv("S3_ACCESS_KEY_ID", "minioadmin")
        self.secret_key = os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin123")
        self.region = os.getenv("S3_REGION", "us-east-1")
        # Bucket names Rules:
        # Allowed: lowercase letters, numbers, and hyphens
        # Not allowed: uppercase characters or underscores
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "minio-files")
        
        # Validate bucket name
        is_valid, errors = validate_bucket_name(self.bucket_name)
        if not is_valid:
            raise ValueError(f"Invalid bucket name: {errors}")
        
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
        object_key: str, 
        bucket_name: str = None, 
        expiration: int = 3600,
        method: str = 'GET'
    ) -> Optional[str]:
        """Generate a presigned URL for object access"""
        try:
            if not bucket_name:
                bucket_name = self.bucket_name
                
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
        
    def upload_file_bytes(self, file_data: bytes, bucket_name: str, object_key: str) -> bool:
        """Upload a file to MinIO"""
        try:
            self.client.upload_fileobj(file_data, bucket_name, object_key)
            logger.info(f"Uploaded '{file_data}' to bucket '{bucket_name}' as '{object_key}'")
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
try:
    global minio_config
    minio_config = MinIOConfig()
except Exception as e:
    print(f"❌ Failed to initialize MinIOConfig: {e}")
    raise