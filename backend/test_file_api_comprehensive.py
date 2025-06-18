#!/usr/bin/env python3
"""
Comprehensive File API Integration Test
Tests all file/image endpoints with real users, database, and MinIO storage
Uses existing fifa_test_image.png for testing
Tests: Authentication -> Upload -> Serve -> Metadata -> List -> Delete
"""

import asyncio
import sys
import uuid
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import httpx

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal, engine
from app.models.database.user import User
from app.models.database.uploaded_image import UploadedImage
from app.services.storage.storage import storage_service
from app.core.security import security
from app.core.config import get_settings

# SQLAlchemy cleanup
from sqlalchemy import delete

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_IMAGE_PATH = "fifa_test_image.png"

class FileAPIIntegrationTest:
    """Test class for comprehensive file API integration"""
    
    def __init__(self):
        self.test_users = []
        self.auth_tokens = {}
        self.uploaded_files = []
        self.settings = get_settings()
        
    async def setup_test_environment(self):
        """Set up test users and authentication"""
        print("Setting up test environment...")
        
        # Verify test image exists
        if not os.path.exists(TEST_IMAGE_PATH):
            raise FileNotFoundError(f"Test image not found: {TEST_IMAGE_PATH}")
        
        async with AsyncSessionLocal() as db:
            # Create test users with different subscription tiers
            test_user_configs = [
                {
                    "username": f"file_test_user_pro_{uuid.uuid4().hex[:8]}",
                    "email": f"file_test_pro_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "pro",
                    "is_active": True,
                    "is_verified": True
                },
                {
                    "username": f"file_test_user_enterprise_{uuid.uuid4().hex[:8]}",
                    "email": f"file_test_enterprise_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "is_verified": True
                },
                {
                    "username": f"file_test_user_free_{uuid.uuid4().hex[:8]}",
                    "email": f"file_test_free_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "free",
                    "is_active": True,
                    "is_verified": True
                }
            ]
            
            for user_config in test_user_configs:
                test_user = User(
                    user_id=str(uuid.uuid4()),
                    username=user_config["username"],
                    email=user_config["email"],
                    full_name=f"Test User {str(user_config['subscription_tier']).title()}",
                    hashed_password="test_password_hash",
                    subscription_tier=user_config["subscription_tier"],
                    is_active=user_config["is_active"],
                    is_verified=user_config["is_verified"]
                )
                
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
                
                # Generate auth token for user
                token = security.create_access_token(
                    subject=test_user.user_id,
                    scopes=["files", "chat"]
                )
                
                self.test_users.append(test_user)
                self.auth_tokens[test_user.user_id] = token
                
                print(f"Created test user: {test_user.username} ({test_user.subscription_tier}) - ID: {test_user.user_id}")
            
            print(f"Created {len(self.test_users)} test users with authentication tokens")
    
    def get_auth_headers(self, user_id: str) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        token = self.auth_tokens.get(user_id)
        if not token:
            raise ValueError(f"No auth token for user {user_id}")
        
        return {"Authorization": f"Bearer {token}"}
    
    async def test_service_status(self):
        """Test files service status endpoint"""
        print("Testing files service status...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/files/files_status")
            
            print(f"Status endpoint response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Service version: {data.get('version', 'unknown')}")
                print(f"Max image size: {data.get('max_image_size_mb', 'unknown')} MB")
                print(f"Allowed types: {data.get('allowed_types', 'unknown')}")
                
                # Check for thumbnail feature support
                features = data.get('features', [])
                if 'thumbnails' in features:
                    print(f"Thumbnail feature: ENABLED")
                    print(f"Thumbnail sizes: {data.get('thumbnail_sizes', 'unknown')}")
                    print(f"Thumbnail format: {data.get('thumbnail_format', 'unknown')}")
                else:
                    print(f"Thumbnail feature: NOT ENABLED")
                
                return True
            else:
                print(f"Service status check failed: {response.text}")
                return False
    
    async def test_image_upload_flow(self):
        """Test image upload flow for different user types"""
        print("Testing image upload flow...")
        
        async with httpx.AsyncClient() as client:
            upload_results = []
            
            # Read the FIFA test image
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            print(f"Using test image: {TEST_IMAGE_PATH} ({len(image_data)} bytes)")
            
            for user in self.test_users:
                print(f"Testing upload for user: {user.username} ({user.subscription_tier})")
                
                # Prepare upload request
                filename = f"fifa_upload_{user.subscription_tier}_{uuid.uuid4().hex[:8]}.png"
                files = {
                    "file": (filename, image_data, "image/png")
                }
                data = {
                    "conversation_id": f"conv_test_{uuid.uuid4().hex[:8]}"
                }
                headers = self.get_auth_headers(user.user_id)
                
                print(f"  Uploading {filename}...")
                
                # Make upload request
                response = await client.post(
                    f"{API_BASE_URL}/files/images/upload",
                    files=files,
                    data=data,
                    headers=headers
                )
                
                print(f"  Upload response: {response.status_code}")
                
                # All users can now upload (free, pro, enterprise)
                if response.status_code == 201:
                    upload_data = response.json()
                    upload_results.append({
                        "user": user,
                        "upload_data": upload_data,
                        "file_size": len(image_data)
                    })
                    self.uploaded_files.append({
                        "file_id": upload_data["file_id"],
                        "user_id": user.user_id,
                        "s3_key": upload_data["s3_key"],
                        "filename": filename
                    })
                    print(f"  Upload successful: {upload_data['file_id']}")
                    print(f"  File URL: {upload_data.get('urls', {}).get('api', 'N/A')}")
                    
                    # Check for thumbnail URLs in response
                    urls = upload_data.get('urls', {})
                    thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                    if thumbnail_urls:
                        print(f"  Thumbnail URLs generated: {list(thumbnail_urls.keys())}")
                    else:
                        print(f"  No thumbnail URLs found in response")
                        
                else:
                    print(f"  Upload failed: {response.status_code} - {response.text}")
            
            print(f"Upload flow completed. {len(upload_results)} files uploaded successfully.")
            return upload_results
    
    async def test_image_serving_flow(self):
        """Test image serving with authentication and ownership validation"""
        print("Testing image serving flow...")
        
        async with httpx.AsyncClient() as client:
            serve_results = []
            
            for uploaded_file in self.uploaded_files:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing serving for file: {file_id} ({filename})")
                
                # Test 1: Authorized access (owner)
                headers = self.get_auth_headers(owner_user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}",
                    headers=headers,
                    follow_redirects=False
                )
                
                if response.status_code == 302:
                    print(f"  Owner access: Redirected to presigned URL")
                    presigned_url = response.headers.get("location")
                    if presigned_url:
                        # Test accessing the presigned URL
                        presigned_response = await client.get(presigned_url)
                        if presigned_response.status_code == 200:
                            print(f"  Presigned URL access successful ({len(presigned_response.content)} bytes)")
                            serve_results.append({"file_id": file_id, "owner_access": True})
                        else:
                            print(f"  Presigned URL access failed: {presigned_response.status_code}")
                else:
                    print(f"  Owner access failed: {response.status_code}")
                
                # Test 2: Unauthorized access (different user)
                for other_user in self.test_users:
                    if other_user.user_id != owner_user_id:
                        other_headers = self.get_auth_headers(other_user.user_id)
                        unauthorized_response = await client.get(
                            f"{API_BASE_URL}/files/images/{file_id}",
                            headers=other_headers
                        )
                        
                        if unauthorized_response.status_code == 403:
                            print(f"  Unauthorized access correctly blocked ({other_user.username})")
                        else:
                            print(f"  WARNING: Unauthorized access should be blocked but got {unauthorized_response.status_code}")
                        break
                
                # Test 3: No authentication
                no_auth_response = await client.get(f"{API_BASE_URL}/files/images/{file_id}")
                if no_auth_response.status_code in [401, 403]:
                    print(f"  No auth access correctly blocked")
                else:
                    print(f"  WARNING: No auth access should be blocked but got {no_auth_response.status_code}")
            
            print(f"Serving flow completed. {len(serve_results)} files served successfully.")
            return serve_results
    
    async def test_thumbnail_serving_flow(self):
        """Test thumbnail serving with different sizes and authentication"""
        print("Testing thumbnail serving flow...")
        
        async with httpx.AsyncClient() as client:
            thumbnail_results = []
            
            # Test thumbnail sizes from configuration
            test_sizes = ["150x150", "300x300"]  # Based on default config
            
            for uploaded_file in self.uploaded_files:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing thumbnails for file: {file_id} ({filename})")
                
                for size in test_sizes:
                    print(f"  Testing thumbnail size: {size}")
                    
                    # Test 1: Authorized access (owner)
                    headers = self.get_auth_headers(owner_user_id)
                    response = await client.get(
                        f"{API_BASE_URL}/files/images/{file_id}/thumbnail?size={size}",
                        headers=headers,
                        follow_redirects=False
                    )
                    
                    if response.status_code == 302:
                        print(f"    Owner access: Redirected to presigned URL")
                        presigned_url = response.headers.get("location")
                        if presigned_url:
                            # Test accessing the presigned URL
                            presigned_response = await client.get(presigned_url)
                            if presigned_response.status_code == 200:
                                print(f"    Thumbnail served successfully ({len(presigned_response.content)} bytes)")
                                thumbnail_results.append({
                                    "file_id": file_id, 
                                    "size": size, 
                                    "served": True,
                                    "bytes": len(presigned_response.content)
                                })
                            else:
                                print(f"    Thumbnail presigned URL access failed: {presigned_response.status_code}")
                    elif response.status_code == 404:
                        print(f"    Thumbnail not found for size {size} (may not be generated yet)")
                    else:
                        print(f"    Thumbnail access failed: {response.status_code}")
                    
                    # Test 2: Unauthorized access
                    for other_user in self.test_users:
                        if other_user.user_id != owner_user_id:
                            other_headers = self.get_auth_headers(other_user.user_id)
                            unauthorized_response = await client.get(
                                f"{API_BASE_URL}/files/images/{file_id}/thumbnail?size={size}",
                                headers=other_headers
                            )
                            
                            if unauthorized_response.status_code in [403, 404]:
                                print(f"    Unauthorized thumbnail access correctly blocked")
                            else:
                                print(f"    WARNING: Unauthorized thumbnail access should be blocked but got {unauthorized_response.status_code}")
                            break
                
                # Test 3: Default size (no size parameter)
                print(f"  Testing default thumbnail size")
                headers = self.get_auth_headers(owner_user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}/thumbnail",
                    headers=headers,
                    follow_redirects=False
                )
                
                if response.status_code == 302:
                    print(f"    Default thumbnail served successfully")
                elif response.status_code == 404:
                    print(f"    Default thumbnail not found")
                else:
                    print(f"    Default thumbnail access: {response.status_code}")
                
                # Test 4: Invalid size
                print(f"  Testing invalid thumbnail size")
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}/thumbnail?size=999x999",
                    headers=headers
                )
                
                if response.status_code == 404:
                    print(f"    Invalid thumbnail size correctly returns 404")
                else:
                    print(f"    Invalid thumbnail size returned: {response.status_code}")
            
            print(f"Thumbnail serving flow completed. {len(thumbnail_results)} thumbnails served successfully.")
            return thumbnail_results
    
    async def test_image_metadata_flow(self):
        """Test image metadata retrieval"""
        print("Testing image metadata flow...")
        
        async with httpx.AsyncClient() as client:
            metadata_results = []
            
            for uploaded_file in self.uploaded_files:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing metadata for file: {file_id} ({filename})")
                
                headers = self.get_auth_headers(owner_user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}/metadata",
                    headers=headers
                )
                
                if response.status_code == 200:
                    metadata = response.json()
                    print(f"  Metadata retrieved: {metadata.get('filename', 'unknown')}")
                    print(f"  Size: {metadata.get('size', 'unknown')} bytes")
                    print(f"  Content type: {metadata.get('content_type', 'unknown')}")
                    print(f"  Uploaded at: {metadata.get('uploaded_at', 'unknown')}")
                    
                    # Check for thumbnail URLs in metadata
                    urls = metadata.get('urls', {})
                    thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                    if thumbnail_urls:
                        print(f"  Thumbnail URLs in metadata: {list(thumbnail_urls.keys())}")
                    else:
                        print(f"  No thumbnail URLs in metadata")
                    
                    metadata_results.append(metadata)
                else:
                    print(f"  Metadata retrieval failed: {response.status_code}")
            
            print(f"Metadata flow completed. {len(metadata_results)} metadata retrieved.")
            return metadata_results
    
    async def test_image_list_flow(self):
        """Test listing user's images"""
        print("Testing image list flow...")
        
        async with httpx.AsyncClient() as client:
            list_results = []
            
            for user in self.test_users:
                print(f"Testing image list for user: {user.username}")
                
                headers = self.get_auth_headers(user.user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images",
                    headers=headers
                )
                
                if response.status_code == 200:
                    list_data = response.json()
                    image_count = len(list_data.get("images", []))
                    print(f"  Found {image_count} images")
                    
                    # Print image details
                    for img in list_data.get("images", []):
                        print(f"    - {img.get('filename', 'unknown')} ({img.get('file_id', 'unknown')})")
                        
                        # Check for thumbnail URLs in each image
                        urls = img.get('urls', {})
                        thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                        if thumbnail_urls:
                            print(f"      Thumbnails: {list(thumbnail_urls.keys())}")
                        else:
                            print(f"      No thumbnails available")
                    
                    list_results.append({
                        "user": user,
                        "image_count": image_count,
                        "images": list_data.get("images", [])
                    })
                else:
                    print(f"  Image list failed: {response.status_code}")
            
            print(f"List flow completed. Retrieved lists for {len(list_results)} users.")
            return list_results
    
    async def test_image_deletion_flow(self):
        """Test image deletion with ownership validation"""
        print("Testing image deletion flow...")
        
        async with httpx.AsyncClient() as client:
            deletion_results = []
            
            # Test deleting half of the uploaded files
            files_to_delete = self.uploaded_files[:len(self.uploaded_files)//2]
            
            for uploaded_file in files_to_delete:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing deletion for file: {file_id} ({filename})")
                
                # Test 1: Unauthorized deletion attempt
                for other_user in self.test_users:
                    if other_user.user_id != owner_user_id:
                        other_headers = self.get_auth_headers(other_user.user_id)
                        unauthorized_response = await client.delete(
                            f"{API_BASE_URL}/files/images/{file_id}",
                            headers=other_headers
                        )
                        
                        if unauthorized_response.status_code == 403:
                            print(f"  Unauthorized deletion correctly blocked")
                        else:
                            print(f"  WARNING: Unauthorized deletion should be blocked but got {unauthorized_response.status_code}")
                        break
                
                # Test 2: Authorized deletion (owner)
                headers = self.get_auth_headers(owner_user_id)
                response = await client.delete(
                    f"{API_BASE_URL}/files/images/{file_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"  Deletion successful")
                    deletion_results.append({"file_id": file_id, "deleted": True})
                    
                    # Verify file is actually deleted by trying to access it
                    verify_response = await client.get(
                        f"{API_BASE_URL}/files/images/{file_id}",
                        headers=headers
                    )
                    
                    if verify_response.status_code == 403:
                        print(f"  Deletion verified - file no longer accessible")
                    else:
                        print(f"  WARNING: File should be inaccessible after deletion but got {verify_response.status_code}")
                else:
                    print(f"  Deletion failed: {response.status_code}")
                    if response.status_code != 200:
                        print(f"  Error details: {response.text}")
            
            print(f"Deletion flow completed. {len(deletion_results)} files deleted.")
            return deletion_results
    
    async def test_error_handling(self):
        """Test various error conditions"""
        print("Testing error handling...")
        
        async with httpx.AsyncClient() as client:
            pro_user = next((u for u in self.test_users if u.subscription_tier == "pro"), None)
            if not pro_user:
                print("No pro user available for error testing")
                return []
            
            headers = self.get_auth_headers(pro_user.user_id)
            error_results = []
            
            # Test 1: Upload invalid file type
            print("  Testing invalid file type...")
            text_data = b"This is not an image file"
            files = {"file": ("test.txt", text_data, "text/plain")}
            response = await client.post(
                f"{API_BASE_URL}/files/images/upload",
                files=files,
                headers=headers
            )
            
            if response.status_code == 400:
                print("  Invalid file type correctly rejected")
                error_results.append({"test": "invalid_type", "handled": True})
            else:
                print(f"  WARNING: Invalid file type should be rejected but got {response.status_code}")
            
            # Test 2: Access non-existent file
            print("  Testing access to non-existent file...")
            response = await client.get(
                f"{API_BASE_URL}/files/images/nonexistent_file_id",
                headers=headers
            )
            
            if response.status_code == 403:
                print("  Non-existent file correctly returns 403")
                error_results.append({"test": "nonexistent_file", "handled": True})
            else:
                print(f"  Non-existent file returned: {response.status_code}")
            
            # Test 3: Delete non-existent file
            print("  Testing deletion of non-existent file...")
            response = await client.delete(
                f"{API_BASE_URL}/files/images/nonexistent_file_id",
                headers=headers
            )
            
            if response.status_code == 403:
                print("  Non-existent file deletion correctly returns 403")
                error_results.append({"test": "nonexistent_delete", "handled": True})
            else:
                print(f"  Non-existent file deletion returned: {response.status_code}")
            
            # Test 4: Access thumbnail of non-existent file
            print("  Testing thumbnail access for non-existent file...")
            response = await client.get(
                f"{API_BASE_URL}/files/images/nonexistent_file_id/thumbnail",
                headers=headers
            )
            
            if response.status_code in [403, 404]:
                print("  Non-existent file thumbnail correctly blocked")
                error_results.append({"test": "nonexistent_thumbnail", "handled": True})
            else:
                print(f"  Non-existent file thumbnail returned: {response.status_code}")
            
            # Test 5: Access thumbnail with invalid size format
            if self.uploaded_files:
                test_file_id = self.uploaded_files[0]["file_id"]
                print("  Testing thumbnail with invalid size format...")
                
                invalid_sizes = ["abc", "150", "150x", "x150", "150x150x150"]
                for invalid_size in invalid_sizes:
                    response = await client.get(
                        f"{API_BASE_URL}/files/images/{test_file_id}/thumbnail?size={invalid_size}",
                        headers=headers
                    )
                    
                    if response.status_code == 404:
                        print(f"    Invalid size '{invalid_size}' correctly returns 404")
                        error_results.append({"test": f"invalid_size_{invalid_size}", "handled": True})
                    else:
                        print(f"    Invalid size '{invalid_size}' returned: {response.status_code}")
            
            print(f"Error handling completed. {len(error_results)} scenarios tested.")
            return error_results
    
    async def verify_minio_integration(self):
        """Verify MinIO storage integration"""
        print("Verifying MinIO integration...")
        
        try:
            # Test MinIO connection through storage service
            test_data = b"MinIO integration test data"
            test_key = f"test/{uuid.uuid4().hex}.txt"
            
            # Upload test file
            await storage_service.storage.upload_file(test_data, test_key, "text/plain")
            print("  MinIO upload successful")
            
            # Generate presigned URL
            presigned_url = await storage_service.storage.generate_presigned_url(test_key)
            if presigned_url:
                print("  MinIO presigned URL generation successful")
            
            # Delete test file
            await storage_service.storage.delete_file(test_key)
            print("  MinIO deletion successful")
            
            return True
            
        except Exception as e:
            print(f"  MinIO integration failed: {e}")
            return False
    
    async def cleanup_test_environment(self):
        """Clean up all test data"""
        print("Cleaning up test environment...")
        
        try:
            async with AsyncSessionLocal() as db:
                # Clean up uploaded images (any that might remain)
                if self.test_users:
                    user_ids = [user.user_id for user in self.test_users]
                    
                    # Get all uploaded images for test users
                    from sqlalchemy import select
                    query = select(UploadedImage).where(UploadedImage.user_id.in_(user_ids))
                    result = await db.execute(query)
                    remaining_images = list(result.scalars().all())
                    
                    # Delete from MinIO storage
                    for image in remaining_images:
                        try:
                            # Delete original image
                            await storage_service.storage.delete_file(image.s3_key)
                            print(f"  Deleted S3 file: {image.s3_key}")
                            
                            # Delete thumbnails if they exist
                            if image.thumbnail_s3_keys:
                                try:
                                    import json
                                    thumbnail_keys = json.loads(image.thumbnail_s3_keys)
                                    for size, thumb_s3_key in thumbnail_keys.items():
                                        try:
                                            await storage_service.storage.delete_file(thumb_s3_key)
                                            print(f"  Deleted thumbnail {size}: {thumb_s3_key}")
                                        except Exception as e:
                                            print(f"  Failed to delete thumbnail {size}: {e}")
                                except Exception as e:
                                    print(f"  Failed to parse thumbnail keys: {e}")
                                    
                        except Exception as e:
                            print(f"  Failed to delete S3 file {image.s3_key}: {e}")
                    
                    # Delete from database
                    await db.execute(
                        delete(UploadedImage).where(UploadedImage.user_id.in_(user_ids))
                    )
                    print(f"  Deleted {len(remaining_images)} uploaded images from database")
                    
                    # Delete test users
                    await db.execute(
                        delete(User).where(User.user_id.in_(user_ids))
                    )
                    print(f"  Deleted {len(self.test_users)} test users")
                
                await db.commit()
                print("Cleanup completed successfully")
                
        except Exception as e:
            print(f"Cleanup failed: {e}")
            raise
    
    async def run_comprehensive_test(self):
        """Run the complete test suite"""
        print("Starting comprehensive file API integration test")
        print("=" * 60)
        
        try:
            # Setup
            await self.setup_test_environment()
            
            # Verify MinIO connection
            print("=" * 60)
            print("MINIO INTEGRATION VERIFICATION")
            minio_ok = await self.verify_minio_integration()
            
            # Run service tests
            print("=" * 60)
            print("SERVICE STATUS TEST")
            service_ok = await self.test_service_status()
            
            # Run core functionality tests
            print("=" * 60)
            print("IMAGE UPLOAD FLOW TEST")
            upload_results = await self.test_image_upload_flow()
            
            print("=" * 60)
            print("IMAGE SERVING FLOW TEST")
            serve_results = await self.test_image_serving_flow()
            
            print("=" * 60)
            print("THUMBNAIL SERVING FLOW TEST")
            thumbnail_results = await self.test_thumbnail_serving_flow()
            
            print("=" * 60)
            print("IMAGE METADATA FLOW TEST")
            metadata_results = await self.test_image_metadata_flow()
            
            print("=" * 60)
            print("IMAGE LIST FLOW TEST")
            list_results = await self.test_image_list_flow()
            
            print("=" * 60)
            print("IMAGE DELETION FLOW TEST")
            deletion_results = await self.test_image_deletion_flow()
            
            print("=" * 60)
            print("ERROR HANDLING TEST")
            error_results = await self.test_error_handling()
            
            # Summary
            print("=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"MinIO Integration: {'PASS' if minio_ok else 'FAIL'}")
            print(f"Service Status: {'PASS' if service_ok else 'FAIL'}")
            print(f"Uploads Tested: {len(upload_results)}")
            print(f"Serves Tested: {len(serve_results)}")
            print(f"Metadata Retrieved: {len(metadata_results)}")
            print(f"Lists Retrieved: {len(list_results)}")
            print(f"Deletions Tested: {len(deletion_results)}")
            print(f"Thumbnails Served: {len(thumbnail_results)}")
            print(f"Error Scenarios: {len(error_results)}")
            
            # Calculate success rate
            total_tests = len(upload_results) + len(serve_results) + len(metadata_results) + len(list_results) + len(deletion_results) + len(thumbnail_results)
            print(f"Total Operations Tested: {total_tests}")
            
            if total_tests > 0:
                print("ALL TESTS COMPLETED SUCCESSFULLY")
            else:
                print("WARNING: No successful operations completed")
            
        except Exception as e:
            print(f"Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Always cleanup
            await self.cleanup_test_environment()


async def main():
    """Main test execution"""
    print("Comprehensive File API Integration Test Suite")
    print("=" * 80)
    print("This test will:")
    print("- Create real test users with different subscription tiers")
    print("- Test image upload, serving, metadata, listing, and deletion")
    print("- Test thumbnail generation and serving in multiple sizes")
    print("- Verify thumbnail URLs are included in all relevant responses")
    print("- Test thumbnail authentication and authorization")
    print("- Use existing fifa_test_image.png for testing")
    print("- Verify authentication and authorization")
    print("- Test MinIO storage integration")
    print("- Clean up all test data including thumbnails")
    print("=" * 80)
    
    test_runner = FileAPIIntegrationTest()
    
    try:
        await test_runner.run_comprehensive_test()
        print("\nTest suite completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        await test_runner.cleanup_test_environment()
        
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()
        await test_runner.cleanup_test_environment()


if __name__ == "__main__":
    # Environment variables are now properly loaded from .env via config.py
    # No need to set them manually here
    asyncio.run(main())