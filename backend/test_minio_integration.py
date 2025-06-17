#!/usr/bin/env python3
"""
Test MinIO Integration with ImageStorageService
Verify that our storage service can connect to and use MinIO
"""

import os
import sys
import asyncio
from pathlib import Path

# Set environment variables for testing
os.environ.update({
    "STORAGE_BACKEND": "minio",
    "S3_BUCKET_NAME": "chatgpt-files",
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY_ID": "minioadmin",
    "S3_SECRET_ACCESS_KEY": "minioadmin123",
    "S3_REGION": "us-east-1",
    "MAX_IMAGE_SIZE": "20971520",
    "ALLOWED_IMAGE_TYPES": ".png,.jpg,.jpeg,.gif,.webp",
    "IMAGE_BASE_URL": "http://localhost:8000/api/images"
})

from app.services.storage.storage import ImageStorageService

async def test_minio_connection():
    """Test MinIO connection and basic operations"""
    print("🧪 Testing MinIO Integration...")
    
    try:
        # Initialize storage service
        storage = ImageStorageService()
        print("✅ ImageStorageService initialized")
        
        # Test connection by trying to check if bucket exists
        bucket_name = storage.storage.bucket_name
        print(f"📦 Using bucket: {bucket_name}")
        
        # Create test image data (simple PNG bytes)
        test_image_data = create_test_image_bytes()
        test_filename = "test_image.png"
        content_type = "image/png"
        
        print(f"📝 Creating test file: {test_filename} ({len(test_image_data)} bytes)")
        
        # Test upload
        print("⬆️  Testing image upload...")
        upload_result = await storage.upload_image(
            file_data=test_image_data,
            filename=test_filename,
            content_type=content_type,
            user_id="test_user"
        )
        
        print(f"✅ Upload successful!")
        print(f"   File ID: {upload_result['file_id']}")
        print(f"   S3 Key: {upload_result['s3_key']}")
        print(f"   Display URL: {upload_result['urls']['display']}")
        print(f"   API URL: {upload_result['urls']['api']}")
        
        # Test presigned URL generation
        print("🔗 Testing presigned URL generation...")
        presigned_url = await storage.get_presigned_url(upload_result['s3_key'])
        print(f"✅ Presigned URL generated: {presigned_url[:50]}...")
        
        # Test file deletion
        print("🗑️  Testing file deletion...")
        delete_success = await storage.delete_image(upload_result['s3_key'])
        if delete_success:
            print("✅ File deleted successfully")
        else:
            print("⚠️  File deletion failed")
        
        print("\n🎉 All MinIO integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_test_image_bytes() -> bytes:
    """Create a minimal valid PNG for testing"""
    # This is a minimal 1x1 transparent PNG
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # bit depth, color type, etc.
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk start
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,  # compressed data
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,  # IDAT data
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
        0x42, 0x60, 0x82
    ])
    return png_data

async def test_validation():
    """Test file validation"""
    print("\n🔍 Testing file validation...")
    
    storage = ImageStorageService()
    
    # Test file size validation
    try:
        storage.validate_image_file("test.png", 25 * 1024 * 1024)  # 25MB - too large
        print("❌ Should have failed size validation")
    except ValueError as e:
        print(f"✅ Size validation works: {e}")
    
    # Test file type validation
    try:
        storage.validate_image_file("test.txt", 1000)  # Wrong type
        print("❌ Should have failed type validation")
    except ValueError as e:
        print(f"✅ Type validation works: {e}")
    
    # Test valid file
    try:
        storage.validate_image_file("test.png", 1000)  # Valid
        print("✅ Valid file passes validation")
    except ValueError as e:
        print(f"❌ Valid file should not fail: {e}")

if __name__ == "__main__":
    async def main():
        print("🚀 Starting MinIO Integration Tests\n")
        
        # Test validation first
        await test_validation()
        
        # Test MinIO connection and operations
        success = await test_minio_connection()
        
        if success:
            print("\n🎉 All tests completed successfully!")
            print("✅ MinIO is ready for image upload functionality")
        else:
            print("\n❌ Some tests failed - check MinIO configuration")
            sys.exit(1)
    
    asyncio.run(main()) 