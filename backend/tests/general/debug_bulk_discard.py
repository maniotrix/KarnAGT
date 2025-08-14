#!/usr/bin/env python3
"""
Debug script to test bulk discard functionality
"""

import asyncio
import sys
sys.path.append('.')

from app.services.storage.staging_storage import staging_service

async def test_bulk_discard():
    user_id = "test-user-123"
    
    print("=== BULK DISCARD DEBUG TEST ===")
    
    # Test 1: Upload some files first
    print("1. Uploading test files...")
    test_data = b"fake image data for testing"
    files_data = [
        (test_data, "test1.jpg", "image/jpeg"),
        (test_data, "test2.png", "image/png"),
        (test_data, "test3.gif", "image/gif"),
    ]
    
    try:
        upload_result = await staging_service.bulk_upload_to_staging(
            files_data=files_data,
            user_id=user_id,
            max_concurrent=3
        )
        
        print(f"Upload result: {upload_result['successfully_staged']} successful, {upload_result['failed_uploads']} failed")
        
        if upload_result['successfully_staged'] > 0:
            staging_ids = [f["staging_id"] for f in upload_result["staged_files"]]
            print(f"Staging IDs created: {staging_ids}")
            
            # Test 2: Try bulk discard
            print("\n2. Testing bulk discard...")
            discard_result = await staging_service.bulk_discard_staged_files(
                staging_ids=staging_ids,
                user_id=user_id
            )
            
            print(f"Discard result: {discard_result}")
            
            # Test 3: Try bulk discard again (should all fail)
            print("\n3. Testing bulk discard again (should fail)...")
            discard_result2 = await staging_service.bulk_discard_staged_files(
                staging_ids=staging_ids,
                user_id=user_id
            )
            
            print(f"Second discard result: {discard_result2}")
            
        else:
            print("No files uploaded successfully, cannot test discard")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bulk_discard()) 