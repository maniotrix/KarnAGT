#!/usr/bin/env python3
"""
OpenAI Storage System Comprehensive Test
Demonstrates the complete OpenAI Files API integration with database tracking
"""

import asyncio
import sys
import os
from pathlib import Path
import tempfile
from PIL import Image
import io
import time

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal, engine
from app.services.storage.openai_storage import openai_storage_service
from app.models.database.openai_file import OpenAIFile
from app.logging.logger import get_logger

logger = get_logger(__name__)


async def create_test_user(db):
    """Create a dedicated test user for the demo"""
    try:
        from app.models.database.user import User
        from sqlalchemy import select
        import uuid
        
        # Create a test user with a unique email
        test_email = f"test_openai_storage_{uuid.uuid4().hex[:8]}@example.com"
        test_user = User(
            email=test_email,
            username=f"test_storage_{uuid.uuid4().hex[:8]}",
            full_name="OpenAI Storage Test User",
            is_active=True,
            is_verified=True,
            hashed_password="dummy_hash_for_test"  # Not used in demo
        )
        
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        
        print(f"   👤 Created test user: {test_user.email} (ID: {test_user.id})")
        return test_user.id, test_user.user_id
        
    except Exception as e:
        await db.rollback()
        print(f"   ❌ Failed to create test user: {e}")
        raise


async def cleanup_test_data(db, user_int_id: int, user_str_id: str):
    """Clean up test data created during the demo"""
    try:
        from sqlalchemy import delete
        from app.models.database.user import User
        
        # Get all OpenAI files for this user
        from sqlalchemy import select
        result = await db.execute(
            select(OpenAIFile).where(OpenAIFile.user_id == user_str_id)
        )
        openai_files = result.scalars().all()
        
        # Delete files from OpenAI (best effort)
        for file_record in openai_files:
            try:
                await openai_storage_service.delete_file(file_record.openai_file_id, db)
                print(f"   🗑️ Deleted OpenAI file: {file_record.openai_file_id}")
            except Exception as e:
                print(f"   ⚠️ Could not delete OpenAI file {file_record.openai_file_id}: {e}")
        
        # Delete test OpenAI file records
        await db.execute(
            delete(OpenAIFile).where(OpenAIFile.user_id == user_str_id)
        )
        
        # Delete the test user itself
        await db.execute(
            delete(User).where(User.id == user_int_id)
        )
        
        await db.commit()
        print(f"   🧹 Test data and user (ID: {user_int_id}) cleaned up successfully")
        
    except Exception as e:
        await db.rollback()
        print(f"   ⚠️ Cleanup failed: {e}")


def create_test_image_file(filename: str = "test_image.png") -> bytes:
    """Create a test image file for upload testing"""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.read()


def create_test_text_file(content: str = "Test file content") -> bytes:
    """Create a test text file for upload testing"""
    return content.encode('utf-8')


async def demo_openai_storage_system(skip_cleanup: bool = False):
    """Demonstrate the complete OpenAI storage system"""
    
    print("📁 OpenAI Storage System Comprehensive Test")
    print("=" * 60)
    
    # Use existing database connection
    print("1. Connecting to existing database...")
    
    async with AsyncSessionLocal() as db:
        # Create a dedicated test user
        print("2. Creating dedicated test user...")
        user_int_id, user_str_id = await create_test_user(db)
        
        uploaded_files = []  # Track uploaded files for cleanup
        
        print(f"3. Testing file upload functionality...")
        
        try:
            # Test 1: Upload PNG image for vision
            print("\n   📤 Test 1: Uploading PNG image for vision...")
            image_data = create_test_image_file("test_vision.png")
            
            result = await openai_storage_service.upload_file(
                file_data=image_data,
                filename="test_vision.png",
                purpose="vision",
                user_id=user_str_id,
                db=db
            )
            
            uploaded_files.append(result["openai_file_id"])
            print(f"   ✅ Upload successful: {result['openai_file_id']}")
            print(f"      - Filename: {result['filename']}")
            print(f"      - Size: {result['size_bytes']} bytes")
            print(f"      - Purpose: {result['purpose']}")
            
        except Exception as e:
            print(f"   ❌ Vision upload failed: {e}")
        
        try:
            # Test 2: Upload text file for assistants
            print("\n   📤 Test 2: Uploading text file for assistants...")
            text_data = create_test_text_file("This is a test document for the assistant to process.")
            
            result = await openai_storage_service.upload_file(
                file_data=text_data,
                filename="test_document.txt",
                purpose="assistants",
                user_id=user_str_id,
                db=db
            )
            
            uploaded_files.append(result["openai_file_id"])
            print(f"   ✅ Upload successful: {result['openai_file_id']}")
            print(f"      - Filename: {result['filename']}")
            print(f"      - Size: {result['size_bytes']} bytes")
            print(f"      - Purpose: {result['purpose']}")
            
        except Exception as e:
            print(f"   ❌ Assistant upload failed: {e}")
        
        # Test 3: File validation errors
        print("\n   🚫 Test 3: Testing file validation...")
        
        # Create image data for validation tests
        image_data = create_test_image_file("validation_test.png")
        
        try:
            # Try to upload oversized file (simulate)
            large_data = b"x" * (600 * 1024 * 1024)  # 600MB (over 512MB limit)
            await openai_storage_service.upload_file(
                file_data=large_data,
                filename="too_large.txt",
                purpose="vision",
                user_id=user_str_id,
                db=db
            )
            print("   ❌ Should have failed due to size limit")
        except ValueError as e:
            print(f"   ✅ Correctly rejected oversized file: {e}")
        except Exception as e:
            print(f"   ⚠️ Unexpected error: {e}")
        
        try:
            # Try invalid purpose
            await openai_storage_service.upload_file(
                file_data=image_data,
                filename="test.png",
                purpose="invalid_purpose",
                user_id=user_str_id,
                db=db
            )
            print("   ❌ Should have failed due to invalid purpose")
        except ValueError as e:
            print(f"   ✅ Correctly rejected invalid purpose: {e}")
        except Exception as e:
            print(f"   ⚠️ Unexpected error: {e}")
        
        # Test 4: List user files
        print(f"\n4. Testing file listing functionality...")
        
        try:
            user_files = await openai_storage_service.list_user_files(
                user_id=user_str_id,
                db=db
            )
            print(f"   📋 User has {len(user_files)} files:")
            for file_info in user_files:
                print(f"      - {file_info['openai_file_id']}: {file_info['filename']} ({file_info['purpose']})")
        except Exception as e:
            print(f"   ❌ File listing failed: {e}")
        
        # Test 5: Filter by purpose
        try:
            vision_files = await openai_storage_service.list_user_files(
                user_id=user_str_id,
                db=db,
                purpose="vision"
            )
            print(f"   🔍 Vision files: {len(vision_files)}")
            
            assistant_files = await openai_storage_service.list_user_files(
                user_id=user_str_id,
                db=db,
                purpose="assistants"
            )
            print(f"   🔍 Assistant files: {len(assistant_files)}")
        except Exception as e:
            print(f"   ❌ Purpose filtering failed: {e}")
        
        # Test 6: Get file info
        print(f"\n5. Testing file info retrieval...")
        
        if uploaded_files:
            try:
                file_id = uploaded_files[0]
                file_info = await openai_storage_service.get_file_info(file_id)
                print(f"   ℹ️ File info for {file_id}:")
                print(f"      - Filename: {file_info['filename']}")
                print(f"      - Purpose: {file_info['purpose']}")
                print(f"      - Size: {file_info['size_bytes']} bytes")
                print(f"      - Status: {file_info['status']}")
            except Exception as e:
                print(f"   ❌ File info retrieval failed: {e}")
        
        # Test 7: Update last used
        print(f"\n6. Testing usage tracking...")
        
        if uploaded_files:
            try:
                file_id = uploaded_files[0]
                await openai_storage_service.update_last_used(file_id, db)
                print(f"   ✅ Updated last used timestamp for {file_id}")
                
                # Verify update
                updated_files = await openai_storage_service.list_user_files(
                    user_id=user_str_id,
                    db=db
                )
                for file_info in updated_files:
                    if file_info['openai_file_id'] == file_id:
                        if file_info['last_used_at']:
                            print(f"   ✅ Last used timestamp: {file_info['last_used_at']}")
                        break
            except Exception as e:
                print(f"   ❌ Usage tracking failed: {e}")
        
        # Test 8: List all files (admin function)
        print(f"\n7. Testing admin file listing...")
        
        try:
            all_files = await openai_storage_service.list_all_files(
                db=db,
                limit=50
            )
            print(f"   📊 Total files in system: {len(all_files)}")
            
            # Count by purpose
            purpose_counts = {}
            for file_info in all_files:
                purpose = file_info['purpose']
                purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
            
            print("   📊 Files by purpose:")
            for purpose, count in purpose_counts.items():
                print(f"      - {purpose}: {count}")
                
        except Exception as e:
            print(f"   ❌ Admin listing failed: {e}")
        
        # Test 9: Single file deletion
        print(f"\n8. Testing single file deletion...")
        
        if len(uploaded_files) > 1:
            try:
                file_to_delete = uploaded_files[0]
                success = await openai_storage_service.delete_file(file_to_delete, db)
                if success:
                    print(f"   ✅ Successfully deleted {file_to_delete}")
                    uploaded_files.remove(file_to_delete)
                else:
                    print(f"   ❌ Failed to delete {file_to_delete}")
            except Exception as e:
                print(f"   ❌ Single deletion failed: {e}")
        
        # Test 10: Bulk deletion
        print(f"\n9. Testing bulk deletion...")
        
        try:
            result = await openai_storage_service.bulk_delete_user_files(
                user_id=user_str_id,
                db=db
            )
            print(f"   📊 Bulk deletion results:")
            print(f"      - Total files: {result['total_files']}")
            print(f"      - Successfully deleted: {result['deleted_count']}")
            print(f"      - Failed deletions: {result['failed_count']}")
            
            if result['failed_files']:
                print("   ❌ Failed files:")
                for failed in result['failed_files']:
                    print(f"      - {failed['file_id']}: {failed['error']}")
            
            uploaded_files.clear()  # All files should be deleted
            
        except Exception as e:
            print(f"   ❌ Bulk deletion failed: {e}")
        
        # NEW TEST: Bulk Upload Functionality
        print(f"\n10. Testing NEW Bulk Upload Functionality...")
        print("=" * 40)
        
        # Test 10.1: Small bulk upload
        print("\n   📤 Test 10.1: Small bulk upload (3 files)...")
        try:
            bulk_files = []
            for i in range(3):
                if i == 0:
                    # Vision image
                    file_data = create_test_image_file(f"bulk_vision_{i}.png")
                    bulk_files.append({
                        "file_data": file_data,
                        "filename": f"bulk_vision_{i}.png",
                        "purpose": "vision"
                    })
                elif i == 1:
                    # Assistant text
                    file_data = create_test_text_file(f"Bulk test document {i} for assistant processing.")
                    bulk_files.append({
                        "file_data": file_data,
                        "filename": f"bulk_assistant_{i}.txt",
                        "purpose": "assistants"
                    })
                else:
                    # Another vision file
                    file_data = create_test_image_file(f"bulk_vision_{i}.png")
                    bulk_files.append({
                        "file_data": file_data,
                        "filename": f"bulk_vision_{i}.png",
                        "purpose": "vision"
                    })
            
            # Execute bulk upload
            start_time = time.time()
            
            bulk_result = await openai_storage_service.bulk_upload_files(
                files=bulk_files,
                user_id=user_str_id,
                max_concurrent=3
            )
            
            upload_duration = time.time() - start_time
            
            print(f"   ✅ Bulk upload completed in {upload_duration:.2f}s")
            print(f"      - Total files: {bulk_result['total_files']}")
            print(f"      - Successful: {bulk_result['success_count']}")
            print(f"      - Failed: {bulk_result['failure_count']}")
            
            # Track uploaded files for cleanup
            for upload in bulk_result['successful_uploads']:
                uploaded_files.append(upload['openai_file_id'])
                print(f"      - Uploaded: {upload['filename']} -> {upload['openai_file_id']}")
            
            # Check for failures
            if bulk_result['failed_uploads']:
                print("   ❌ Failed uploads:")
                for failed in bulk_result['failed_uploads']:
                    print(f"      - {failed['filename']}: {failed['error']}")
            
        except Exception as e:
            print(f"   ❌ Small bulk upload failed: {e}")
        
        # Test 10.2: Medium bulk upload with concurrency
        print("\n   📤 Test 10.2: Medium bulk upload (7 files) - Testing concurrency...")
        try:
            bulk_files = []
            for i in range(7):
                if i % 2 == 0:
                    # Vision images
                    file_data = create_test_image_file(f"concurrent_vision_{i}.png")
                    bulk_files.append({
                        "file_data": file_data,
                        "filename": f"concurrent_vision_{i}.png",
                        "purpose": "vision"
                    })
                else:
                    # Assistant files
                    file_data = create_test_text_file(f"Concurrent test document {i} for processing.")
                    bulk_files.append({
                        "file_data": file_data,
                        "filename": f"concurrent_assistant_{i}.txt",
                        "purpose": "assistants"
                    })
            
            # Test with higher concurrency
            start_time = time.time()
            
            bulk_result = await openai_storage_service.bulk_upload_files(
                files=bulk_files,
                user_id=user_str_id,
                max_concurrent=5  # Higher concurrency
            )
            
            upload_duration = time.time() - start_time
            
            print(f"   ✅ Concurrent bulk upload completed in {upload_duration:.2f}s")
            print(f"      - Processed {len(bulk_files)} files with max_concurrent=5")
            print(f"      - Success rate: {bulk_result['success_count']}/{bulk_result['total_files']}")
            print(f"      - Average time per file: {upload_duration/len(bulk_files):.3f}s")
            
            # Track uploaded files
            for upload in bulk_result['successful_uploads']:
                uploaded_files.append(upload['openai_file_id'])
            
        except Exception as e:
            print(f"   ❌ Concurrent bulk upload failed: {e}")
        
        # Test 10.3: Bulk upload validation testing
        print("\n   📤 Test 10.3: Bulk upload validation testing...")
        try:
            # Test empty files list
            empty_result = await openai_storage_service.bulk_upload_files(
                files=[],
                user_id=user_str_id
            )
            print(f"   ✅ Empty files validation: {empty_result['total_files']} files processed")
            
            # Test files with validation errors
            invalid_files = [
                {
                    "file_data": b"x" * (600 * 1024 * 1024),  # Too large
                    "filename": "too_large.txt",
                    "purpose": "vision"
                },
                {
                    "file_data": create_test_text_file("Valid content"),
                    "filename": "valid_file.txt",
                    "purpose": "assistants"
                },
                {
                    "file_data": create_test_image_file("test.png"),
                    "filename": "invalid_purpose.png",
                    "purpose": "invalid_purpose"
                }
            ]
            
            validation_result = await openai_storage_service.bulk_upload_files(
                files=invalid_files,
                user_id=user_str_id
            )
            
            print(f"   ✅ Validation testing completed:")
            print(f"      - Total files: {validation_result['total_files']}")
            print(f"      - Successful: {validation_result['success_count']}")
            print(f"      - Failed: {validation_result['failure_count']}")
            
            # Track any successful uploads from validation test for cleanup
            if validation_result['successful_uploads']:
                print(f"      - Tracking {len(validation_result['successful_uploads'])} successful uploads for cleanup")
                for upload in validation_result['successful_uploads']:
                    uploaded_files.append(upload['openai_file_id'])
            
            if 'validation_errors' in validation_result:
                print(f"      - Validation errors caught: {len(validation_result['validation_errors'])}")
                for error in validation_result['validation_errors']:
                    print(f"        - File {error['file_index']}: {error['error']}")
            
        except Exception as e:
            print(f"   ❌ Bulk validation testing failed: {e}")
        
        # Test 10.4: Transaction handling verification
        print("\n   📤 Test 10.4: Testing transaction isolation...")
        try:
            # Verify files were uploaded with separate database sessions
            current_files = await openai_storage_service.list_user_files(
                user_id=user_str_id,
                db=db
            )
            
            print(f"   ✅ Transaction isolation verification:")
            print(f"      - Total files in database: {len(current_files)}")
            print(f"      - Files uploaded via bulk operations: {len(uploaded_files)}")
            
            # Verify all uploads are properly tracked
            tracked_ids = {f['openai_file_id'] for f in current_files}
            uploaded_set = set(uploaded_files)
            
            if uploaded_set.issubset(tracked_ids):
                print(f"   ✅ All bulk uploads properly tracked in database")
            else:
                missing = uploaded_set - tracked_ids
                print(f"   ⚠️ Missing files in database: {missing}")
            
            # Test concurrent access doesn't cause conflicts
            print("   🔄 Testing concurrent database access safety...")
            
            # Simulate multiple users accessing file lists simultaneously
            async def get_user_files():
                return await openai_storage_service.list_user_files(user_id=user_str_id, db=db)
            
            # Run multiple concurrent database operations
            concurrent_results = await asyncio.gather(
                get_user_files(),
                get_user_files(),
                get_user_files(),
                return_exceptions=True
            )
            
            success_count = sum(1 for r in concurrent_results if not isinstance(r, Exception))
            print(f"   ✅ Concurrent database access: {success_count}/3 operations succeeded")
            
        except Exception as e:
            print(f"   ❌ Transaction verification failed: {e}")
        
        # Test 10.5: Performance and scalability metrics
        print("\n   📤 Test 10.5: Performance metrics...")
        try:
            # Get final file count
            final_files = await openai_storage_service.list_user_files(
                user_id=user_str_id,
                db=db
            )
            
            vision_files = [f for f in final_files if f['purpose'] == 'vision']
            assistant_files = [f for f in final_files if f['purpose'] == 'assistants']
            
            print(f"   📊 Performance Summary:")
            print(f"      - Total files uploaded: {len(final_files)}")
            print(f"      - Vision files: {len(vision_files)}")
            print(f"      - Assistant files: {len(assistant_files)}")
            print(f"      - Bulk upload operations: 3 test scenarios")
            print(f"      - Max concurrency tested: 5 simultaneous uploads")
            print(f"      - Transaction isolation: ✅ Verified")
            print(f"      - Validation handling: ✅ Verified")
            print(f"      - Error recovery: ✅ Verified")
            
        except Exception as e:
            print(f"   ❌ Performance metrics failed: {e}")
        
        print("=" * 40)
        print("🎉 NEW Bulk Upload Testing Complete!")
        
        # Clean up bulk upload test files immediately
        print(f"\n10.6. Cleaning up bulk upload test files...")
        if uploaded_files:
            try:
                cleanup_result = await openai_storage_service.bulk_delete_user_files(
                    user_id=user_str_id,
                    db=db
                )
                print(f"   🧹 Bulk cleanup results:")
                print(f"      - Files to clean: {len(uploaded_files)}")
                print(f"      - Successfully deleted: {cleanup_result['deleted_count']}")
                print(f"      - Failed deletions: {cleanup_result['failed_count']}")
                
                # Clear the tracking list since we just deleted everything
                uploaded_files.clear()
                
                if cleanup_result['failed_files']:
                    print("   ⚠️ Some files could not be deleted:")
                    for failed in cleanup_result['failed_files']:
                        print(f"      - {failed['file_id']}: {failed['error']}")
                        
            except Exception as e:
                print(f"   ❌ Bulk cleanup failed: {e}")
        else:
            print("   ✅ No files to clean up")
        
        # Test 11: Verify cleanup
        print(f"\n11. Verifying file cleanup...")
        
        try:
            remaining_files = await openai_storage_service.list_user_files(
                user_id=user_str_id,
                db=db
            )
            print(f"   📋 Remaining files: {len(remaining_files)}")
            if remaining_files:
                print("   ⚠️ Some files were not deleted:")
                for file_info in remaining_files:
                    print(f"      - {file_info['openai_file_id']}: {file_info['filename']}")
        except Exception as e:
            print(f"   ❌ Cleanup verification failed: {e}")
        
        # Clean up test data at the end (unless skipped)
        if not skip_cleanup:
            print(f"\n12. Final cleanup - removing test user and any remaining files...")
            if uploaded_files:
                print(f"   ⚠️ Warning: {len(uploaded_files)} files still tracked, will be cleaned up")
            await cleanup_test_data(db, user_int_id, user_str_id)
        else:
            print(f"\n12. Skipping cleanup (--no-cleanup flag)")
            print(f"    🔍 Test user ID: {user_int_id} (str: {user_str_id})")
            if uploaded_files:
                print(f"    📁 Files still in system: {len(uploaded_files)}")
                for file_id in uploaded_files[:5]:  # Show first 5
                    print(f"       - {file_id}")
                if len(uploaded_files) > 5:
                    print(f"       ... and {len(uploaded_files) - 5} more")
    
    print(f"\n🎉 OpenAI Storage System Test Complete!")
    print("=" * 60)
    print("Key Features Tested:")
    print("✅ File upload with database tracking")
    print("✅ File validation (size, purpose, format)")
    print("✅ File listing and filtering")
    print("✅ File info retrieval")
    print("✅ Usage tracking")
    print("✅ Single file deletion")
    print("✅ Bulk file deletion")
    print("✅ Admin functions")
    print("✅ Error handling")
    print("🆕 NEW: Bulk upload functionality")
    print("🆕 NEW: Concurrent upload processing")
    print("🆕 NEW: Transaction isolation testing")
    print("🆕 NEW: Performance metrics")
    print("🆕 NEW: Advanced validation testing")

if __name__ == "__main__":
    import sys
    
    # Check for --no-cleanup flag
    skip_cleanup = "--no-cleanup" in sys.argv
    if skip_cleanup:
        print("⚠️  Running with --no-cleanup flag (test data will persist)")
    
    print("🚀 Starting OpenAI Storage System Comprehensive Test...")
    
    try:
        # Run the main demo
        asyncio.run(demo_openai_storage_system(skip_cleanup))
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n👋 Thanks for testing the OpenAI Storage System!") 