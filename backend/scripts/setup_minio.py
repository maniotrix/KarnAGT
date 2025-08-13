#!/usr/bin/env python3
"""
MinIO Setup Script
Configures MinIO buckets and policies after service startup
"""

import os
import time
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


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

# MinIO configuration
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"

# Main bucket for image and file storage
# Bucket names Rules:
# Allowed: lowercase letters, numbers, and hyphens
# Not allowed: uppercase characters or underscores
BUCKET_NAME = "minio-files"

# NOTE: WARNING: This script should be only used in local environment, not in docker containers

def create_minio_client():
    """Create MinIO client"""
    return boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

def wait_for_minio():
    """Wait for MinIO to be ready"""
    print("Waiting for MinIO to be ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            client = create_minio_client()
            client.list_buckets()
            print("✅ MinIO is ready!")
            return True
        except Exception as e:
            print(f"⏳ Attempt {attempt + 1}/{max_attempts}: MinIO not ready yet...")
            time.sleep(2)
    
    print("❌ MinIO failed to start within timeout")
    return False

def create_bucket(client, bucket_name):
    """Create a bucket if it doesn't exist"""
    print(f"🔍 Debug - Bucket name: {bucket_name}")
    is_valid, errors = validate_bucket_name(bucket_name)
    if not is_valid:
        print(f"❌ Invalid bucket name: {errors}")
        return False
    try:
        client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' already exists")
        return True
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        print(f"🔍 Debug - Error code: {error_code}, Error: {e}")
        if error_code == 404:
            # Bucket doesn't exist, create it
            try:
                client.create_bucket(Bucket=bucket_name)
                print(f"✅ Created bucket '{bucket_name}'")
                return True
            except ClientError as create_error:
                print(f"❌ Failed to create bucket '{bucket_name}': {create_error}")
                return False
        else:
            print(f"❌ Error checking bucket '{bucket_name}': {e}")
            return False

def setup_bucket_policy(client, bucket_name):
    """Set up bucket policy for public read access (for images)"""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    
    try:
        import json
        client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(policy)
        )
        print(f"✅ Set public read policy for bucket '{bucket_name}'")
    except ClientError as e:
        print(f"⚠️  Failed to set policy for bucket '{bucket_name}': {e}")

def main():
    """Main setup function"""
    print("🚀 Starting MinIO setup...")
    print(f"🔧 Endpoint: {MINIO_ENDPOINT}")
    print(f"👤 Access Key: {MINIO_ACCESS_KEY}")
    print(f"📦 Target Bucket: {BUCKET_NAME}")
    
    # Wait for MinIO to be ready
    if not wait_for_minio():
        return False
    
    # Create client
    client = create_minio_client()
    
    # Create the main bucket
    success = create_bucket(client, BUCKET_NAME)
    if success:
        # Set up bucket policy for public access (for images)
        setup_bucket_policy(client, BUCKET_NAME)
    
    if success:
        print("🎉 MinIO setup completed successfully!")
        print(f"📊 MinIO Console: http://localhost:9001")
        print(f"🔧 API Endpoint: {MINIO_ENDPOINT}")
        print(f"👤 Access Key: {MINIO_ACCESS_KEY}")
        print(f"🔑 Secret Key: {MINIO_SECRET_KEY}")
    else:
        print("❌ MinIO setup completed with errors")
    
    return success

if __name__ == "__main__":
    main() 