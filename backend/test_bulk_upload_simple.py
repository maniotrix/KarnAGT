#!/usr/bin/env python3
"""
Simple Bulk Upload Test
Tests the bulk upload functionality with a smaller, more focused test
"""

import asyncio
import sys
import uuid
import os
from pathlib import Path

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.models.database.uploaded_image import UploadedImage
from app.services.storage.storage import storage_service
from app.core.security import security

# SQLAlchemy cleanup
from sqlalchemy import delete, select

# Test configuration
TEST_IMAGE_PATH = "fifa_test_image.png"

async def test_bulk_upload():
    """Simple test of bulk upload functionality"""
    print("Simple Bulk Upload Test")
    print("=" * 50)
    
    # Verify test image exists
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"❌ Test image not found: {TEST_IMAGE_PATH}")
        return False
    
    test_user = None
    uploaded_files = []
    
    try:
        async with AsyncSessionLocal() as db:
            # Create a test user
            test_user = User(
                user_id=str(uuid.uuid4()),
                username=f"bulk_test_user_{uuid.uuid4().hex[:8]}",
                email=f"bulk_test_{uuid.uuid4().hex[:8]}@example.com",
                full_name="Bulk Test User",
                hashed_password="test_password_hash",
                subscription_tier="pro",
                is_active=True,
                is_verified=True
            )
            
            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)
            
            print(f"✅ Created test user: {test_user.username}")
        
        # Read test image
        with open(TEST_IMAGE_PATH, 'rb') as f:
            image_data = f.read()
        
        print(f"✅ Loaded test image: {len(image_data)} bytes")
        
        # Prepare bulk upload data
        files_data = []
        for i in range(5):  # Test with 5 files
            filename = f"bulk_test_{i}_{uuid.uuid4().hex[:8]}.png"
            files_data.append((image_data, filename, "image/png"))
        
        print(f"✅ Prepared {len(files_data)} files for bulk upload")
        
        # Perform bulk upload
        async with AsyncSessionLocal() as db:
            print("🚀 Starting bulk upload...")
            result = await storage_service.bulk_upload_images(
                files_data=files_data,
                user_id=test_user.user_id,
                db=db,
                conversation_id=None,
                max_concurrent=3,
                generate_thumbnails=True
            )
            
            print(f"✅ Bulk upload completed!")
            print(f"   Total requested: {result['total_requested']}")
            print(f"   Successfully uploaded: {result['successfully_uploaded']}")
            print(f"   Failed uploads: {result['failed_uploads']}")
            print(f"   Upload duration: {result['upload_duration_seconds']:.2f}s")
            print(f"   Quota consumed: ${result['quota_consumed_usd']:.4f}")
            
            # Store file IDs for cleanup
            uploaded_files = [img["file_id"] for img in result["uploaded_images"]]
            
            if result['successfully_uploaded'] == len(files_data):
                print("🎉 All files uploaded successfully!")
                success = True
            else:
                print(f"⚠️  Only {result['successfully_uploaded']}/{len(files_data)} files uploaded")
                if result['failed_images']:
                    print("   Failed images:")
                    for failed in result['failed_images']:
                        print(f"     - {failed.get('filename', 'unknown')}: {failed.get('error', 'unknown error')}")
                success = False
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        try:
            async with AsyncSessionLocal() as db:
                if uploaded_files:
                    # Delete uploaded images
                    query = select(UploadedImage).where(UploadedImage.file_id.in_(uploaded_files))
                    result = await db.execute(query)
                    images = list(result.scalars().all())
                    
                    for image in images:
                        try:
                            # Delete from storage
                            await storage_service.storage.delete_file(image.s3_key)
                            
                            # Delete thumbnails
                            if image.thumbnail_s3_keys is not None:
                                import json
                                thumbnail_keys = json.loads(image.thumbnail_s3_keys)
                                for thumb_s3_key in thumbnail_keys.values():
                                    await storage_service.storage.delete_file(thumb_s3_key)
                                    
                        except Exception as e:
                            print(f"     Warning: Failed to delete storage for {image.file_id}: {e}")
                    
                    # Delete from database
                    await db.execute(
                        delete(UploadedImage).where(UploadedImage.file_id.in_(uploaded_files))
                    )
                    print(f"   ✅ Deleted {len(images)} uploaded images")
                
                if test_user:
                    # Delete test user
                    await db.execute(
                        delete(User).where(User.user_id == test_user.user_id)
                    )
                    print(f"   ✅ Deleted test user")
                
                await db.commit()
                print("✅ Cleanup completed successfully")
                
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")


async def main():
    """Main test execution"""
    print("Testing bulk upload functionality with database session fix...")
    
    success = await test_bulk_upload()
    
    if success:
        print("\n🎊 Test PASSED! Bulk upload is working correctly.")
        return 0
    else:
        print("\n❌ Test FAILED! There are still issues with bulk upload.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 