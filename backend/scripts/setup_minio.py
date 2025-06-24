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

# MinIO configuration
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"

# Main bucket for image and file storage
BUCKET_NAME = "chatgpt-files"

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
    try:
        client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' already exists")
        return True
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
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