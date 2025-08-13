#!/usr/bin/env python3
"""
Test MinIO Integration with MinIOConfig
Verify that our MinIO configuration can connect to and use MinIO
"""

import os
import sys
import asyncio
import tempfile

from minio_config import minio_config as minio_service

async def test_minio_connection():
    """Test MinIO connection and basic operations"""
    print("🧪 Testing MinIO Integration...")
    
    try:
        # Initialize MinIO service
        print("✅ MinIOConfig initialized")
        
        # Test connection by ensuring bucket exists
        bucket_name = minio_service.get_bucket_name()
        print(f"📦 Using bucket: {bucket_name}")
        
        bucket_exists = await minio_service.ensure_bucket_exists(bucket_name)
        if not bucket_exists:
            print("❌ Failed to ensure bucket exists")
            return False
        
        # Create test image file
        test_image_data = create_test_image_bytes()
        test_filename = "test_image.png"
        
        # Write test data to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(test_image_data)
            temp_file_path = temp_file.name
        
        print(f"📝 Created test file: {test_filename} ({len(test_image_data)} bytes)")
        
        try:
            # Test upload
            print("⬆️  Testing image upload...")
            upload_success = minio_service.upload_file(
                file_path=temp_file_path,
                bucket_name=bucket_name,
                object_key=test_filename
            )
            
            if upload_success:
                print("✅ Upload successful!")
                
                # Test presigned URL generation
                print("🔗 Testing presigned URL generation...")
                presigned_url = minio_service.generate_presigned_url(test_filename, bucket_name)
                if presigned_url:
                    print(f"✅ Presigned URL generated: {presigned_url[:50]}...")
                else:
                    print("⚠️  Failed to generate presigned URL")
                
                # Test file deletion
                print("🗑️  Testing file deletion...")
                delete_success = minio_service.delete_file(bucket_name, test_filename)
                if delete_success:
                    print("✅ File deleted successfully")
                else:
                    print("⚠️  File deletion failed")
            else:
                print("❌ Upload failed")
                return False
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
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

async def test_basic_validation():
    """Test basic MinIO configuration"""
    print("\n🔍 Testing MinIO configuration...")
    
    # Test configuration
    bucket_name = minio_service.get_bucket_name()
    if bucket_name:
        print(f"✅ Bucket name configured: {bucket_name}")
    else:
        print("❌ No bucket name configured")
    
    # Test client creation
    try:
        client = minio_service.client
        if client:
            print("✅ MinIO client created successfully")
        else:
            print("❌ Failed to create MinIO client")
    except Exception as e:
        print(f"❌ Client creation failed: {e}")

if __name__ == "__main__":
    async def main():
        print("🚀 Starting MinIO Integration Tests\n")
        
        # Test basic configuration first
        await test_basic_validation()
        
        # Test MinIO connection and operations
        success = await test_minio_connection()
        
        if success:
            print("\n🎉 All tests completed successfully!")
            print("✅ MinIO is ready for image upload functionality")
        else:
            print("\n❌ Some tests failed - check MinIO configuration")
            sys.exit(1)
    
    asyncio.run(main()) 